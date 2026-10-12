"""Host-free tests for shared event-handler registration and cleanup."""

import importlib.util
import os
import sys
import types
import unittest


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
EVENTS_PATH = os.path.join(REPO_ROOT, "pyrevitlib", "pyrevit", "revit", "events.py")


class _ArrayList(list):
    def Add(self, value):
        self.append(value)


class _Hashtable(dict):
    @property
    def Keys(self):
        return list(self)

    @property
    def Count(self):
        return len(self)

    def ContainsKey(self, key):
        return key in self

    def Remove(self, key):
        self.pop(key, None)


class _AppDomain:
    def __init__(self):
        self.data = {}

    def GetData(self, key):
        return self.data.get(key)

    def SetData(self, key, value):
        self.data[key] = value


class _EventHook:
    def __init__(self):
        self.handlers = []
        self.fail_removals = set()

    def __iadd__(self, handler):
        self.handlers.append(handler)
        return self

    def __isub__(self, handler):
        if handler in self.fail_removals:
            raise RuntimeError("simulated Revit event removal failure")
        self.handlers.remove(handler)
        return self


class _Application:
    def __init__(self):
        self.DocumentChanged = _EventHook()
        self.DocumentClosed = _EventHook()
        self.DocumentOpened = _EventHook()


class _UIApplication:
    def __init__(self):
        self.ViewActivated = _EventHook()
        self.SelectionChanged = _EventHook()


class _HostApplication:
    def __init__(self):
        self._api_context = True
        self._app = _Application()
        self._uiapp = _UIApplication()

    @property
    def has_api_context(self):
        return self._api_context

    @property
    def app(self):
        return self._app if self._api_context else None

    @property
    def uiapp(self):
        return self._uiapp if self._api_context else None

    def is_older_than(self, version):
        return False


class _ExternalEvent:
    def __init__(self, handler):
        self.handler = handler
        self.response = "Accepted"

    def Raise(self):
        return self.response


class _ExternalEventFactory:
    @staticmethod
    def Create(handler):
        return _ExternalEvent(handler)


class _Logger:
    def __init__(self):
        self.errors = []

    def error(self, message, *args):
        self.errors.append(message % args if args else message)


class _EventHandlerFactory:
    def __getitem__(self, event_args_type):
        return lambda handler: handler


def _module(name, **values):
    result = types.ModuleType(name)
    for key, value in values.items():
        setattr(result, key, value)
    return result


def load_events_module(app_domain, host, exec_id, logger, external_event_response):
    """Import the production events module with isolated host and CLR doubles."""
    system_collections = _module(
        "System.Collections", ArrayList=_ArrayList, Hashtable=_Hashtable
    )
    system = _module("System")
    system.Collections = system_collections

    pyrevit = _module(
        "pyrevit",
        HOST_APP=host,
        EXEC_PARAMS=types.SimpleNamespace(exec_id=exec_id),
        DB=types.SimpleNamespace(
            Events=types.SimpleNamespace(
                DocumentChangedEventArgs=type("DocChangedArgs", (), {}),
                DocumentClosedEventArgs=type("DocClosedArgs", (), {}),
                DocumentOpenedEventArgs=type("DocOpenedArgs", (), {}),
            )
        ),
        UI=types.SimpleNamespace(
            IExternalEventHandler=type("IExternalEventHandler", (), {}),
            Events=types.SimpleNamespace(
                ViewActivatedEventArgs=type("ViewActivatedArgs", (), {}),
                SelectionChangedEventArgs=type("SelectionChangedArgs", (), {}),
            ),
            ExternalEvent=_ExternalEventFactory,
            ExternalEventRequest=types.SimpleNamespace(
                Denied="Denied", TimedOut="TimedOut"
            ),
        ),
        framework=types.SimpleNamespace(
            AppDomain=types.SimpleNamespace(CurrentDomain=app_domain),
            EventHandler=_EventHandlerFactory(),
        ),
        compat=types.SimpleNamespace(IRONPY=False),
        PyRevitCPythonNotSupported=RuntimeError,
    )
    coreutils = _module("pyrevit.coreutils")
    logger_module = _module("pyrevit.coreutils.logger", get_logger=lambda name: logger)
    pyrevit.coreutils = coreutils

    replacements = {
        "System": system,
        "System.Collections": system_collections,
        "pyrevit": pyrevit,
        "pyrevit.coreutils": coreutils,
        "pyrevit.coreutils.logger": logger_module,
    }
    previous = {key: sys.modules.get(key) for key in replacements}
    sys.modules.update(replacements)
    try:
        module_name = "pyrevit_test_events_{}".format(exec_id)
        spec = importlib.util.spec_from_file_location(module_name, EVENTS_PATH)
        events = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(events)
    finally:
        for key, old_module in previous.items():
            if old_module is None:
                sys.modules.pop(key, None)
            else:
                sys.modules[key] = old_module

    events.HANDLER_UNREGISTERER_EXTEVENT.response = external_event_response
    return events


class EventHandlerCleanupTests(unittest.TestCase):
    """Cover cross-engine cleanup, failures, and API-context routing."""

    def setUp(self):
        """Create a fresh shared registry and Revit application double."""
        self.app_domain = _AppDomain()
        self.host = _HostApplication()
        self.logger = _Logger()

    def _load(self, exec_id, response="Accepted"):
        return load_events_module(
            self.app_domain, self.host, exec_id, self.logger, response
        )

    def test_reload_removes_handlers_when_script_skipped_stop_events(self):
        """A later engine unregisters handlers left by an abnormal script exit."""
        script_events = self._load("script-execution")
        script_events.handle("view-activated")(lambda sender, args: None)
        registered_handler = self.host._uiapp.ViewActivated.handlers[0]

        reload_events = self._load("reload-execution")
        reload_events.unregister_all_exec_handlers()

        self.assertNotIn(registered_handler, self.host._uiapp.ViewActivated.handlers)
        self.assertIsNone(
            self.app_domain.GetData(reload_events._REGISTERED_HANDLERS_KEY)
        )

        next_handler = lambda sender, args: None
        script_events.register_handler(
            "view-activated", next_handler, "next-script-execution"
        )
        next_registered_handler = self.host._uiapp.ViewActivated.handlers[-1]
        next_reload_events = self._load("next-reload-execution")
        next_reload_events.unregister_all_exec_handlers()
        self.assertNotIn(
            next_registered_handler, self.host._uiapp.ViewActivated.handlers
        )

    def test_duplicate_subscriptions_are_all_removed(self):
        """Cleanup detaches each delegate registered for the same event."""
        events = self._load("script-execution")
        events.register_handler("view-activated", lambda *_: None, "exec")
        events.register_handler("view-activated", lambda *_: None, "exec")
        self.assertEqual(len(self.host._uiapp.ViewActivated.handlers), 2)

        events.unregister_all_exec_handlers()

        self.assertEqual(self.host._uiapp.ViewActivated.handlers, [])

    def test_removal_failure_does_not_block_other_groups_or_reload(self):
        """Log a failing detach, release its registry group, and continue."""
        events = self._load("reload-execution")
        events.register_handler("view-activated", lambda *_: None, "failed-exec")
        events.register_handler("doc-opened", lambda *_: None, "healthy-exec")
        failed_handler = self.host._uiapp.ViewActivated.handlers[0]
        self.host._uiapp.ViewActivated.fail_removals.add(failed_handler)

        events.unregister_all_exec_handlers()

        self.assertEqual(self.host._app.DocumentOpened.handlers, [])
        self.assertIn(failed_handler, self.host._uiapp.ViewActivated.handlers)
        self.assertTrue(self.logger.errors)
        self.assertIsNone(self.app_domain.GetData(events._REGISTERED_HANDLERS_KEY))

    def test_non_api_reload_routes_cleanup_through_external_event(self):
        """Perform Revit event removal only when the deferred API callback runs."""
        events = self._load("reload-execution")
        events.register_handler("view-activated", lambda *_: None, "script-exec")
        registered_handler = self.host._uiapp.ViewActivated.handlers[0]
        self.host._api_context = False

        events.unregister_all_exec_handlers()

        self.assertIn(registered_handler, self.host._uiapp.ViewActivated.handlers)
        self.host._api_context = True
        events.HANDLER_UNREGISTERER.Execute(None)
        self.assertNotIn(registered_handler, self.host._uiapp.ViewActivated.handlers)
        self.assertIsNone(self.app_domain.GetData(events._REGISTERED_HANDLERS_KEY))

    def test_denied_external_event_does_not_block_cleanup_caller(self):
        """Log a denied request and release tracked delegates without raising."""
        events = self._load("reload-execution", response="Denied")
        events.register_handler("view-activated", lambda *_: None, "script-exec")
        self.host._api_context = False

        events.unregister_all_exec_handlers()

        self.assertTrue(self.logger.errors)
        self.assertIsNone(self.app_domain.GetData(events._REGISTERED_HANDLERS_KEY))


if __name__ == "__main__":
    unittest.main()
