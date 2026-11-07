"""Host-free tests for shared event-handler registration and cleanup."""

TEST_ENVIRONMENT = "HostFree"
TEST_LEVEL = "Integration"


import importlib.util
import os
import sys
import types
import unittest
from pathlib import Path


REPO_ROOT = str(Path(__file__).resolve().parents[4])
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


class _EventInfo:
    def __init__(self, name):
        self.name = name

    def AddEventHandler(self, source, handler):
        hook = getattr(source, self.name)
        hook += handler

    def RemoveEventHandler(self, source, handler):
        hook = getattr(source, self.name)
        hook -= handler


class _EventSourceType:
    def GetEvent(self, name):
        return _EventInfo(name)


class _EventSource:
    def GetType(self):
        return _EventSourceType()


class _Application(_EventSource):
    def __init__(self):
        self.DocumentChanged = _EventHook()
        self.DocumentClosed = _EventHook()
        self.DocumentOpened = _EventHook()


class _UIApplication(_EventSource):
    def __init__(self):
        self.ViewActivated = _EventHook()
        self.SelectionChanged = _EventHook()


class _HostApplication:
    @property
    def has_api_context(self):
        return self._api_context

    @property
    def app(self):
        return self._app if self._api_context else None

    @property
    def uiapp(self):
        return self._uiapp if self._api_context else None

    def __init__(self, revit_year=2026):
        self.revit_year = revit_year
        self._api_context = True
        self._app = _Application()
        self._uiapp = _UIApplication()

    def is_older_than(self, version):
        return self.revit_year < version


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


def load_events_module(
    app_domain,
    host,
    exec_id,
    logger,
    external_event_response,
    has_selection_changed_args=True,
):
    """Import the production events module with isolated host and CLR doubles."""
    ui_events = types.SimpleNamespace(
        ViewActivatedEventArgs=type("ViewActivatedArgs", (), {})
    )
    if has_selection_changed_args:
        ui_events.SelectionChangedEventArgs = type("SelectionChangedArgs", (), {})
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
            Events=ui_events,
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
    envvars = _module(
        "pyrevit.coreutils.envvars",
        REGISTEREDEVENTHANDLERS_ENVVAR="PYREVIT_REGISTEREDEVENTHANDLERS",
    )
    logger_module = _module("pyrevit.coreutils.logger", get_logger=lambda name: logger)
    pyrevit.coreutils = coreutils
    coreutils.envvars = envvars

    replacements = {
        "System": system,
        "System.Collections": system_collections,
        "pyrevit": pyrevit,
        "pyrevit.coreutils": coreutils,
        "pyrevit.coreutils.envvars": envvars,
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
            self.app_domain.GetData(
                reload_events.envvars.REGISTEREDEVENTHANDLERS_ENVVAR
            )
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
        self.assertIsNone(
            self.app_domain.GetData(events.envvars.REGISTEREDEVENTHANDLERS_ENVVAR)
        )

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
        self.assertIsNone(
            self.app_domain.GetData(events.envvars.REGISTEREDEVENTHANDLERS_ENVVAR)
        )

    def test_denied_external_event_does_not_block_cleanup_caller(self):
        """Keep handlers tracked and subscribed when an external event is denied."""
        events = self._load("reload-execution", response="Denied")
        events.register_handler("view-activated", lambda *_: None, "script-exec")
        registered_handler = self.host._uiapp.ViewActivated.handlers[0]
        self.host._api_context = False

        events.unregister_all_exec_handlers()

        self.assertTrue(self.logger.errors)
        self.assertIn(registered_handler, self.host._uiapp.ViewActivated.handlers)
        registered_handlers = self.app_domain.GetData(
            events.envvars.REGISTEREDEVENTHANDLERS_ENVVAR
        )
        self.assertIn("script-exec", registered_handlers)
        self.assertIn(
            registered_handler,
            registered_handlers["script-exec"]["view-activated"],
        )


class PreSelectionChangedHostTests(unittest.TestCase):
    """Revit 2021/2022 lack ``UI.Events.SelectionChangedEventArgs``."""

    def setUp(self):
        """Load the events module against a Revit 2022 API surface."""
        self.logger = _Logger()
        self.host = _HostApplication(revit_year=2022)
        self.events = load_events_module(
            _AppDomain(),
            self.host,
            "revit-2022",
            self.logger,
            "Accepted",
            has_selection_changed_args=False,
        )

    def test_selection_changed_is_refused_with_an_error(self):
        """Attaching the missing event logs instead of raising."""
        self.assertIsNone(self.events.add_handler("selection-changed", print))
        self.events.remove_handler("selection-changed", print)
        self.assertEqual(2, len(self.logger.errors))
        self.assertEqual([], self.host._uiapp.SelectionChanged.handlers)

    def test_other_events_still_attach(self):
        """Events that exist on older hosts keep working."""
        handler = self.events.add_handler("view-activated", print)
        self.assertIn(handler, self.host._uiapp.ViewActivated.handlers)


class _RaisingExternalEvent:
    def Raise(self):
        raise RuntimeError("raise failed")


class ExecuteInRevitContextTests(unittest.TestCase):
    """Report whether a callback was queued and run it only when it was."""

    def setUp(self):
        """Install the handler and event the IronPython import path creates."""
        self.logger = _Logger()
        self.events = load_events_module(
            _AppDomain(), _HostApplication(), "context-exec", self.logger, "Accepted"
        )
        self.events._HANDLER = self.events._GenericExternalEventHandler()
        self.external_event = _ExternalEvent(self.events._HANDLER)
        self.events._EXTERNAL_EVENT = self.external_event
        self.calls = []

    def _callback(self, *args, **kwargs):
        self.calls.append((args, kwargs))

    def test_accepted_request_queues_and_runs_callback(self):
        """An accepted request returns True and runs the callback on Execute."""
        queued = self.events.execute_in_revit_context(self._callback, 1, key="value")

        self.assertTrue(queued)
        self.assertEqual(self.calls, [])
        self.events._HANDLER.Execute(None)
        self.events._HANDLER.Execute(None)
        self.assertEqual(self.calls, [((1,), {"key": "value"})])
        self.assertEqual(self.logger.errors, [])

    def test_denied_request_discards_callback(self):
        """A denied request returns False and never runs the callback."""
        self.external_event.response = "Denied"

        queued = self.events.execute_in_revit_context(self._callback)

        self.assertFalse(queued)
        self.events._HANDLER.Execute(None)
        self.assertEqual(self.calls, [])
        self.assertTrue(self.logger.errors)

    def test_raise_failure_discards_callback(self):
        """A failing Raise returns False and never runs the callback."""
        self.events._EXTERNAL_EVENT = _RaisingExternalEvent()

        queued = self.events.execute_in_revit_context(self._callback)

        self.assertFalse(queued)
        self.events._HANDLER.Execute(None)
        self.assertEqual(self.calls, [])
        self.assertTrue(self.logger.errors)

    def test_missing_external_event_returns_false(self):
        """An ExternalEvent that cannot be created leaves nothing queued."""
        self.events._EXTERNAL_EVENT = None
        self.events.UI.ExternalEvent = types.SimpleNamespace(
            Create=lambda handler: (_ for _ in ()).throw(RuntimeError("no context"))
        )

        queued = self.events.execute_in_revit_context(self._callback)

        self.assertFalse(queued)
        self.events._HANDLER.Execute(None)
        self.assertEqual(self.calls, [])
        self.assertTrue(self.logger.errors)


if __name__ == "__main__":
    unittest.main()
