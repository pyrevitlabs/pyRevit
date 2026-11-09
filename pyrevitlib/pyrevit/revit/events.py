"""Revit events handler management."""

# pylint: disable=unused-argument
import uuid
from System.Collections import ArrayList, Hashtable
from pyrevit import HOST_APP
from pyrevit import EXEC_PARAMS, DB, UI
from pyrevit import framework
from pyrevit import compat
from pyrevit.coreutils import envvars
from pyrevit.coreutils.logger import get_logger
from pyrevit.runtime.types import ApiContextQueue


mlogger = get_logger(__name__)

_CLR_NAMESPACE = "pyrevit.revit.events._" + uuid.uuid4().hex
"""CLR namespace for the handler types this execution of the module defines.

Warning:
    Unique per module execution, not per script execution: pythonnet emits a
    CLR type for each class declaring ``__namespace__`` and refuses a type name
    it already emitted, so re-executing this module in the same interpreter
    (``importlib.reload``, a runner unloading modules) would fail with a fixed
    name, and ``EXEC_PARAMS.exec_id`` repeats within one execution.
"""


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

    __namespace__ = _CLR_NAMESPACE

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


_EVENT_SOURCES = {
    "doc-changed": (DB.Events, "DocumentChangedEventArgs", "app", "DocumentChanged"),
    "doc-closed": (DB.Events, "DocumentClosedEventArgs", "app", "DocumentClosed"),
    "doc-opened": (DB.Events, "DocumentOpenedEventArgs", "app", "DocumentOpened"),
    "view-activated": (
        UI.Events,
        "ViewActivatedEventArgs",
        "uiapp",
        "ViewActivated",
    ),
    "selection-changed": (
        UI.Events,
        "SelectionChangedEventArgs",
        "uiapp",
        "SelectionChanged",
    ),
}


def _event_args_type(event_name):
    """Resolve the event-args type only when a handler is attached.

    Note:
        ``SelectionChangedEventArgs`` exists only in Revit 2023+, so resolving
        it at import time would break ``pyrevit.revit`` on older hosts.
    """
    namespace, type_name, _, _ = _EVENT_SOURCES[event_name]
    return getattr(namespace, type_name)


def _clr_event(event_name):
    """Return the event source object and its CLR ``EventInfo``.

    Handlers are added and removed through ``EventInfo`` so the delegate itself
    is subscribed. Revit returns a new ``Application`` wrapper on every access,
    and CPython's ``-=`` only finds handlers added through the same wrapper.
    """
    _, _, source_name, clr_event_name = _EVENT_SOURCES[event_name]
    source = getattr(HOST_APP, source_name)
    return source, source.GetType().GetEvent(clr_event_name)


def add_handler(event_name, handler_func):
    """Subscribe a function to a Revit event.

    Requires Revit API context. The delegate is attached through the CLR
    ``EventInfo``, so ``remove_handler`` can detach it although Revit returns a
    new ``Application`` wrapper on every access.

    Args:
        event_name (str): key such as ``doc-changed`` or ``selection-changed``.
        handler_func (Callable): called with ``(sender, args)``.

    Returns:
        (EventHandler | None): the subscribed delegate to pass to
            ``remove_handler``; None for an unknown event name, or for
            ``selection-changed`` before Revit 2023, which also logs an error.
    """
    if event_name not in _EVENT_SOURCES:
        return None
    if event_name == "selection-changed" and HOST_APP.is_older_than(2023):
        mlogger.error("Not available in this Revit Version")
        return None
    event_handler = create_handler(handler_func, _event_args_type(event_name))
    source, clr_event = _clr_event(event_name)
    clr_event.AddEventHandler(source, event_handler)
    return event_handler


def remove_handler(event_name, event_handler):
    """Unsubscribe a delegate returned by ``add_handler``.

    Requires Revit API context. Does nothing for an unknown event name, and
    logs an error for ``selection-changed`` before Revit 2023.

    Args:
        event_name (str): the key the delegate was added under.
        event_handler (EventHandler): the delegate ``add_handler`` returned.
    """
    if event_name not in _EVENT_SOURCES:
        return
    if event_name == "selection-changed" and HOST_APP.is_older_than(2023):
        mlogger.error("Not available in this Revit Version")
        return
    source, clr_event = _clr_event(event_name)
    clr_event.RemoveEventHandler(source, event_handler)


def replace_handler(slot, source, event_name, handler_func, handler_args_type):
    """Subscribe to a CLR event, first detaching what ``slot`` subscribed before.

    For smart button ``__selfinit__`` functions, which run again in a new
    engine on every reload. A handler a previous load left subscribed fires
    once more per reload, and keeps that engine and every module it imported
    alive for the rest of the Revit session.

    Args:
        slot (str): process-wide key, unique to this subscription.
        source (object): object raising the event, such as ``__rvt__``.
        event_name (str): CLR event name, such as ``ViewActivated``.
        handler_func (Callable): called with ``(sender, args)``.
        handler_args_type (type): the event's ``EventArgs`` type.

    Returns:
        (EventHandler): the subscribed delegate.
    """
    release_handler(slot, source, event_name)
    event_handler = create_handler(handler_func, handler_args_type)
    source.GetType().GetEvent(event_name).AddEventHandler(source, event_handler)
    framework.AppDomain.CurrentDomain.SetData(slot, event_handler)
    return event_handler


def release_handler(slot, source, event_name):
    """Detach the delegate ``replace_handler`` subscribed under ``slot``.

    Args:
        slot (str): the key passed to ``replace_handler``.
        source (object): object raising the event.
        event_name (str): CLR event name.
    """
    domain = framework.AppDomain.CurrentDomain
    previous = domain.GetData(slot)
    if previous is None:
        return
    source.GetType().GetEvent(event_name).RemoveEventHandler(source, previous)
    domain.SetData(slot, None)


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
    error = _schedule_in_api_context(
        lambda: _unregister_handler_groups(handler_group_ids)
    )
    if error is None:
        return
    mlogger.error("Could not unregister event handlers: {}".format(error))
    if HOST_APP.has_api_context:
        _unregister_handler_groups(handler_group_ids)


def _schedule_in_api_context(callback):
    """Queue a callback on the runtime's ExternalEvent shared by all engines.

    Note:
        Never create an ExternalEvent with a Python handler at import time:
        Revit keeps the handler until the event is disposed, and the handler
        keeps this engine and every module it imported alive after reloads.

    Returns:
        (str | None): why the callback will never run, or None once queued.
    """
    try:
        response = ApiContextQueue.Schedule(callback)
    except Exception as ex:
        return str(ex)
    if response in (
        UI.ExternalEventRequest.Denied,
        UI.ExternalEventRequest.TimedOut,
    ):
        return "ExternalEvent request was {}".format(response)
    return None


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


def execute_in_revit_context(func, *args, **kwargs):
    """Execute a function in Revit API context using ExternalEvent.

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
            ExternalEvent could not be raised, in which case the callback
            never runs.

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
        except Exception as ex:
            mlogger.error("ExternalEvent error: {}".format(ex))
        finally:
            for k, old in saved.items():
                if old is _MISSING:
                    g.pop(k, None)
                else:
                    g[k] = old

    error = _schedule_in_api_context(_wrapper)
    if error is not None:
        mlogger.error("Could not schedule callback: {}".format(error))
        return False
    return True
