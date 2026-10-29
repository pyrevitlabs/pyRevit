"""Revit events handler management."""

# pylint: disable=unused-argument
from collections import deque
from System.Collections import ArrayList, Hashtable
from pyrevit import HOST_APP
from pyrevit import EXEC_PARAMS, DB, UI
from pyrevit import framework
from pyrevit import compat, PyRevitCPythonNotSupported
from pyrevit.coreutils import envvars
from pyrevit.coreutils.logger import get_logger


mlogger = get_logger(__name__)


def _get_registered_handlers():
    """Return the process-shared registry.

    Initialization relies on pyRevit serializing Revit script loading and event
    registration on the UI thread; concurrent initialization is unsupported.
    """
    registered_handlers = framework.AppDomain.CurrentDomain.GetData(
        envvars.REGISTEREDEVENTHANDLERS_ENVVAR
    )
    if registered_handlers is None:
        registered_handlers = Hashtable()
        framework.AppDomain.CurrentDomain.SetData(
            envvars.REGISTEREDEVENTHANDLERS_ENVVAR, registered_handlers
        )
    return registered_handlers


class FuncAsEventHandler(UI.IExternalEventHandler):
    """Turns a function into an event handler."""

    __namespace__ = EXEC_PARAMS.exec_id

    def __init__(self, handler_func, purge=True):
        self.name = "FuncAsEventHandler"
        self.handler_group_id = None
        self.handler_func = handler_func
        self.purge = purge

    def Execute(self, uiapp):
        if self.handler_func and self.handler_group_id:
            self.handler_func(self.handler_group_id)
            if self.purge:
                self.handler_group_id = self.handler_func = None

    def GetName(self):
        return self.name


def create_handler(handler_func, handler_args_type):
    return framework.EventHandler[handler_args_type](handler_func)


def add_handler(event_name, handler_func):
    event_handler = None

    if event_name == "doc-changed":
        event_handler = create_handler(handler_func, DB.Events.DocumentChangedEventArgs)
        HOST_APP.app.DocumentChanged += event_handler

    elif event_name == "doc-closed":
        event_handler = create_handler(handler_func, DB.Events.DocumentClosedEventArgs)
        HOST_APP.app.DocumentClosed += event_handler

    elif event_name == "doc-opened":
        event_handler = create_handler(handler_func, DB.Events.DocumentOpenedEventArgs)
        HOST_APP.app.DocumentOpened += event_handler

    elif event_name == "view-activated":
        event_handler = create_handler(handler_func, UI.Events.ViewActivatedEventArgs)
        HOST_APP.uiapp.ViewActivated += event_handler

    elif event_name == "selection-changed":
        if HOST_APP.is_older_than(2023):
            mlogger.error("Not available in this Revit Version")
            return
        event_handler = create_handler(
            handler_func, UI.Events.SelectionChangedEventArgs
        )
        HOST_APP.uiapp.SelectionChanged += event_handler

    return event_handler


def remove_handler(event_name, event_handler):
    if event_name == "doc-changed":
        HOST_APP.app.DocumentChanged -= event_handler

    elif event_name == "doc-closed":
        HOST_APP.app.DocumentClosed -= event_handler

    elif event_name == "doc-opened":
        HOST_APP.app.DocumentOpened -= event_handler

    elif event_name == "view-activated":
        HOST_APP.uiapp.ViewActivated -= event_handler

    elif event_name == "selection-changed":
        if HOST_APP.is_older_than(2023):
            mlogger.error("Not available in this Revit Version")
            return
        HOST_APP.uiapp.SelectionChanged -= event_handler


def register_handler(event_name, handler_func, handler_group_id):
    registered_handlers = _get_registered_handlers()
    if not registered_handlers.ContainsKey(handler_group_id):
        registered_handlers[handler_group_id] = Hashtable()
    event_handler = add_handler(event_name, handler_func)
    if event_handler:
        handler_group = registered_handlers[handler_group_id]
        if not handler_group.ContainsKey(event_name):
            handler_group[event_name] = ArrayList()
        handler_group[event_name].Add(event_handler)


def unregister_handler(event_name, handler_func, handler_group_id):
    # 'handler_func' argument only for backwards compat
    registered_handlers = _get_registered_handlers()
    if registered_handlers.ContainsKey(handler_group_id):
        handler_group = registered_handlers[handler_group_id]
    else:
        return
    if handler_group.ContainsKey(event_name):
        event_handlers = handler_group[event_name]
        try:
            for event_handler in list(event_handlers):
                try:
                    remove_handler(event_name, event_handler)
                except Exception as ex:
                    mlogger.error(
                        "Could not unregister %s handler for %s: %s",
                        event_name,
                        handler_group_id,
                        ex,
                    )
        finally:
            handler_group.Remove(event_name)


def _clear_registered_handlers_if_empty(registered_handlers):
    if registered_handlers.Count == 0:
        framework.AppDomain.CurrentDomain.SetData(
            envvars.REGISTEREDEVENTHANDLERS_ENVVAR, None
        )


def unregister_exec_handlers(handler_group_id):
    registered_handlers = _get_registered_handlers()
    try:
        if registered_handlers.ContainsKey(handler_group_id):
            handler_group = registered_handlers[handler_group_id]
            for event_name in list(handler_group.Keys):
                try:
                    unregister_handler(event_name, None, handler_group_id)
                except Exception as ex:
                    mlogger.error(
                        "Could not unregister handlers for %s event in %s: %s",
                        event_name,
                        handler_group_id,
                        ex,
                    )
    finally:
        registered_handlers.Remove(handler_group_id)
        _clear_registered_handlers_if_empty(registered_handlers)


def _unregister_handler_groups(handler_group_ids):
    if not isinstance(handler_group_ids, (list, tuple, ArrayList)):
        handler_group_ids = [handler_group_ids]
    for handler_group_id in handler_group_ids:
        try:
            unregister_exec_handlers(handler_group_id)
        except Exception as ex:
            mlogger.error(
                "Could not unregister event handlers for %s: %s",
                handler_group_id,
                ex,
            )


def unregister_all_exec_handlers():
    """Unregister every tracked execution group, directly or via ExternalEvent."""
    registered_handlers = framework.AppDomain.CurrentDomain.GetData(
        envvars.REGISTEREDEVENTHANDLERS_ENVVAR
    )
    if registered_handlers is None:
        return
    handler_group_ids = list(registered_handlers.Keys)
    if not handler_group_ids:
        _clear_registered_handlers_if_empty(registered_handlers)
        return

    if HOST_APP.has_api_context:
        _unregister_handler_groups(handler_group_ids)
    else:
        delayed_unregister_exec_handlers(handler_group_ids)


def delayed_unregister_exec_handlers(handler_group_id):
    handler_group_ids = (
        handler_group_id
        if isinstance(handler_group_id, (list, tuple, ArrayList))
        else [handler_group_id]
    )
    HANDLER_UNREGISTERER.handler_group_id = handler_group_ids
    ext_event = _get_unregisterer_extevent()
    if ext_event is None:
        mlogger.error(
            "Could not create ExternalEvent; event handlers remain registered"
        )
        if HOST_APP.has_api_context:
            _unregister_handler_groups(handler_group_ids)
        return
    try:
        response = ext_event.Raise()
        if response in (
            UI.ExternalEventRequest.Denied,
            UI.ExternalEventRequest.TimedOut,
        ):
            mlogger.error(
                "Could not unregister event handlers; "
                "ExternalEvent request was {}".format(response)
            )
            if HOST_APP.has_api_context:
                _unregister_handler_groups(handler_group_ids)
    except Exception as ex:
        mlogger.error("Could not unregister event handlers: {}".format(ex))
        if HOST_APP.has_api_context:
            _unregister_handler_groups(handler_group_ids)


def _get_unregisterer_extevent():
    # External events require API context, so retry creation on first use.
    global HANDLER_UNREGISTERER_EXTEVENT
    if HANDLER_UNREGISTERER_EXTEVENT is None:
        try:
            HANDLER_UNREGISTERER_EXTEVENT = UI.ExternalEvent.Create(
                HANDLER_UNREGISTERER
            )
        except Exception:
            HANDLER_UNREGISTERER_EXTEVENT = None
    return HANDLER_UNREGISTERER_EXTEVENT


HANDLER_UNREGISTERER = FuncAsEventHandler(_unregister_handler_groups, purge=False)
# Import can occur outside API context, so event creation may be deferred.
try:
    HANDLER_UNREGISTERER_EXTEVENT = UI.ExternalEvent.Create(HANDLER_UNREGISTERER)
except Exception:
    HANDLER_UNREGISTERER_EXTEVENT = None


def handle(*args):  # pylint: disable=no-method-argument
    def decorator(function):
        def wrapper(*args, **kwargs):
            return function(*args, **kwargs)

        for event_name in args:
            register_handler(event_name, wrapper, EXEC_PARAMS.exec_id)
        return wrapper

    return decorator


def stop_events():
    registered_handlers = framework.AppDomain.CurrentDomain.GetData(
        envvars.REGISTEREDEVENTHANDLERS_ENVVAR
    )
    if registered_handlers is not None and registered_handlers.ContainsKey(
        EXEC_PARAMS.exec_id
    ):
        if HOST_APP.has_api_context:
            unregister_exec_handlers(EXEC_PARAMS.exec_id)
        else:
            # request underegister from external event
            delayed_unregister_exec_handlers(EXEC_PARAMS.exec_id)


class _GenericExternalEventHandler(UI.IExternalEventHandler):
    def __init__(self):
        self._queue = deque()

    def Execute(self, uiapp):
        while self._queue:
            fn = self._queue.popleft()
            try:
                fn()
            except Exception as ex:
                mlogger.error("ExternalEvent error: {}".format(ex))

    def GetName(self):
        return "GenericExternalEventHandler"

    def schedule(self, func):
        self._queue.append(func)

    def discard(self, func):
        try:
            self._queue.remove(func)
            return True
        except ValueError:
            return False


if compat.IRONPY:
    _HANDLER = _GenericExternalEventHandler()
    # Import can occur outside API context, so event creation may be deferred.
    try:
        _EXTERNAL_EVENT = UI.ExternalEvent.Create(_HANDLER)
    except Exception:
        _EXTERNAL_EVENT = None


def _get_execute_extevent():
    global _EXTERNAL_EVENT
    if _EXTERNAL_EVENT is None:
        try:
            _EXTERNAL_EVENT = UI.ExternalEvent.Create(_HANDLER)
        except Exception:
            _EXTERNAL_EVENT = None
    return _EXTERNAL_EVENT


def execute_in_revit_context(func, *args, **kwargs):
    """
    Execute a function in Revit API context using ExternalEvent.

    Use this helper when calling Revit API from modeless dialogs,
    background threads, or any non-Revit context where direct API
    access would raise InvalidOperationException.

    The function executes asynchronously - it returns immediately
    and the function runs when Revit is idle.

    Args:
        func: Function to execute in Revit context
        *args: Positional arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function

    Returns:
        (bool): True when the callback was queued; False when the
            ExternalEvent could not be created or raised, in which case the
            callback never runs.

    Example:
        ```python
        # Simple function call
        execute_in_revit_context(transaction_function, doc, element_id)

        # From modeless dialog button click
        def on_button_click(sender, args):
            execute_in_revit_context(
                modify_elements,
                selected_ids,
                parameter_name="Comments",
                value="Updated"
            )
        ```

    Note:
        This function does not return values from the executed function.
        For return values, use callbacks or shared mutable objects.
    """
    if not compat.IRONPY:
        PyRevitCPythonNotSupported("pyrevit.revit.events.execute_in_revit_context")

    # Snapshot module-level imports from the function's globals at scheduling
    # time. When the ExternalEvent fires asynchronously, the IronPython engine
    # may have cleared the script scope (non-persistent engines) or module
    # references may be stale after extension changes / session reload.
    # This affects any module whose __init__.py uses conditional imports at
    # load time (e.g. forms, revit submodules). Only module-type objects are
    # restored to avoid contaminating mutable script state (doc, uidoc, etc.).
    _module_type = type(compat)
    _saved_modules = {
        k: v for k, v in func.__globals__.items() if type(v) is _module_type
    }

    def _wrapper():
        # types.FunctionType with closures is not supported in IronPython 2,
        # so we do a bounded mutation: save, patch, call, restore.
        _MISSING = object()
        g = func.__globals__
        saved = {
            k: g.get(k, _MISSING) for k in _saved_modules if k not in g or g[k] is None
        }
        for k in saved:
            g[k] = _saved_modules[k]
        try:
            func(*args, **kwargs)
        finally:
            for k, old in saved.items():
                if old is _MISSING:
                    g.pop(k, None)
                else:
                    g[k] = old

    _ext_event = _get_execute_extevent()
    if _ext_event is None:
        mlogger.error("Could not create ExternalEvent; scheduled callback will not run")
        return False

    _HANDLER.schedule(_wrapper)
    try:
        response = _ext_event.Raise()
        if response in (
            UI.ExternalEventRequest.Denied,
            UI.ExternalEventRequest.TimedOut,
        ):
            _HANDLER.discard(_wrapper)
            mlogger.error(
                "Could not schedule callback; ExternalEvent request was {}".format(
                    response
                )
            )
            return False
    except Exception as ex:
        _HANDLER.discard(_wrapper)
        mlogger.error(
            "Could not schedule callback through ExternalEvent: {}".format(ex)
        )
        return False
    return True
