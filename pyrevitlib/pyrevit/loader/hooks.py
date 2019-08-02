"""Hooks management."""
from pyrevit import HOST_APP
from pyrevit.coreutils.loadertypes import EventType, PyRevitHooks


def register_hooks():
    pass
    # PyRevitHooks.RegisterHook(HOST_APP.uiapp, EventType eventType)

def unregister_hooks():
    pass
    # PyRevitHooks.UnRegisterHook(HOST_APP.uiapp, EventType eventType)

