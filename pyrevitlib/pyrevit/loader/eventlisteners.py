"""Event handler management."""
from pyrevit import HOST_APP
from pyrevit.coreutils.loadertypes import PyRevitEventTypes, \
    PyRevitEventListeners


def register_listeners():
        
    PyRevitEventListeners.RegisterEventListener(
        HOST_APP.uiapp,
        PyRevitEventTypes.UIApplication_ViewActivated
        )


def unregister_listerners():
    PyRevitEventListeners.UnegisterEventListeners(
        HOST_APP.uiapp,
        PyRevitEventTypes.UIApplication_ViewActivated
        )
