"""Revit events handler management."""
#pylint: disable=unused-argument
from collections import deque
from pyrevit import HOST_APP
from pyrevit import EXEC_PARAMS, DB, UI
from pyrevit import framework
from pyrevit import compat, PyRevitCPythonNotSupported
from pyrevit.coreutils.logger import get_logger


mlogger = get_logger(__name__)


class FuncAsEventHandler(UI.IExternalEventHandler):
    """Turns a function into an event handler."""
    __namespace__ = EXEC_PARAMS.exec_id

    def __init__(self, handler_func, purge=True):
        self.name = 'FuncAsEventHandler'
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

    if event_name == 'doc-changed':
        event_handler = \
            create_handler(handler_func, DB.Events.DocumentChangedEventArgs)
        HOST_APP.app.DocumentChanged += event_handler

    elif event_name == 'doc-closed':
        event_handler = \
            create_handler(handler_func, DB.Events.DocumentClosedEventArgs)
        HOST_APP.app.DocumentClosed += event_handler

    elif event_name == 'doc-opened':
        event_handler = \
            create_handler(handler_func, DB.Events.DocumentOpenedEventArgs)
        HOST_APP.app.DocumentOpened += event_handler

    elif event_name == 'view-activated':
        event_handler = \
            create_handler(handler_func, UI.Events.ViewActivatedEventArgs)
        HOST_APP.uiapp.ViewActivated += event_handler

    elif event_name == 'selection-changed':
        if HOST_APP.is_older_than(2023):
            mlogger.error("Not available in this Revit Version")
            return
        event_handler = \
            create_handler(handler_func, UI.Events.SelectionChangedEventArgs)
        HOST_APP.uiapp.SelectionChanged += event_handler

    return event_handler


def remove_handler(event_name, event_handler):
    if event_name == 'doc-changed':
        HOST_APP.app.DocumentChanged -= event_handler

    elif event_name == 'doc-closed':
        HOST_APP.app.DocumentClosed -= event_handler

    elif event_name == 'doc-opened':
        HOST_APP.app.DocumentOpened -= event_handler

    elif event_name == 'view-activated':
        HOST_APP.uiapp.ViewActivated -= event_handler

    elif event_name == 'selection-changed':
        if HOST_APP.is_older_than(2023):
            mlogger.error("Not available in this Revit Version")
            return
        HOST_APP.uiapp.SelectionChanged -= event_handler


def register_handler(event_name, handler_func, handler_group_id):
    if handler_group_id not in REGISTERED_HANDLERS:
        REGISTERED_HANDLERS[handler_group_id] = {}
    event_handler = add_handler(event_name, handler_func)
    if event_handler:
        REGISTERED_HANDLERS[handler_group_id][event_name] = event_handler


def unregister_handler(event_name, handler_func, handler_group_id):
    if handler_group_id in REGISTERED_HANDLERS \
            and event_name in REGISTERED_HANDLERS[handler_group_id]:
        event_handler = REGISTERED_HANDLERS[handler_group_id].pop(event_name)
        remove_handler(event_name, event_handler)


def unregister_exec_handlers(handler_group_id):
    if handler_group_id in REGISTERED_HANDLERS:
        for event_name, handler_func in \
                REGISTERED_HANDLERS[handler_group_id].items():
            unregister_handler(event_name, handler_func, handler_group_id)


def delayed_unregister_exec_handlers(handler_group_id):
    HANDLER_UNREGISTERER.handler_group_id = handler_group_id
    HANDLER_UNREGISTERER_EXTEVENT.Raise()


REGISTERED_HANDLERS = {}
HANDLER_UNREGISTERER = \
    FuncAsEventHandler(unregister_exec_handlers, purge=False)
HANDLER_UNREGISTERER_EXTEVENT = \
    UI.ExternalEvent.Create(HANDLER_UNREGISTERER)


def handle(*args): #pylint: disable=no-method-argument
    def decorator(function):
        def wrapper(*args, **kwargs):
            return function(*args, **kwargs)
        for event_name in args:
            register_handler(event_name, wrapper, EXEC_PARAMS.exec_id)
        return wrapper
    return decorator


def stop_events():
    if EXEC_PARAMS.exec_id in REGISTERED_HANDLERS:
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


if compat.IRONPY:
    _HANDLER = _GenericExternalEventHandler()
    _EXTERNAL_EVENT = UI.ExternalEvent.Create(_HANDLER)


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
        k: v for k, v in func.__globals__.items()
        if type(v) is _module_type
    }

    def _wrapper():
        # types.FunctionType with closures is not supported in IronPython 2,
        # so we do a bounded mutation: save, patch, call, restore.
        _MISSING = object()
        g = func.__globals__
        saved = {
            k: g.get(k, _MISSING)
            for k in _saved_modules
            if k not in g or g[k] is None
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

    _HANDLER.schedule(_wrapper)
    _EXTERNAL_EVENT.Raise()
