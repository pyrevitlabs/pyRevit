"""Revit events handler management."""
#pylint: disable=unused-argument
from pyrevit import HOST_APP
from pyrevit import EXEC_PARAMS, DB, UI
from pyrevit import framework
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
