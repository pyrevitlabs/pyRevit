"""Hooks management."""
from pyrevit import HOST_APP
from pyrevit.coreutils import envvars
from pyrevit.runtime.types import EventHooks

from pyrevit.loader import sessioninfo


#pylint: disable=W0703,C0302,C0103


def get_hooks_handler():
    """Get the hook handler environment variable.

    Returns:
        (EventHooks): hook handler
    """
    return envvars.get_pyrevit_env_var(envvars.HOOKSHANDLER_ENVVAR)


def set_hooks_handler(handler):
    """Set the hook handler environment variable.

    Args:
        handler (EventHooks): hook handler
    """
    envvars.set_pyrevit_env_var(envvars.HOOKSHANDLER_ENVVAR, handler)


def get_event_hooks():
    """Get all the event hooks."""
    hooks_handler = get_hooks_handler()
    return hooks_handler.GetAllEventHooks()


def unregister_all_hooks():
    """Unregister all hooks."""
    hooks_handler = get_hooks_handler()
    hooks_handler.UnRegisterAllHooks(uiApp=HOST_APP.uiapp)


def activate():
    """Activate all event hooks."""
    hooks_handler = get_hooks_handler()
    hooks_handler.ActivateEventHooks(uiApp=HOST_APP.uiapp)


def setup_hooks(session_id=None):
    """Setup the hooks for the given session.

    If no session is specified, use the current one.

    Args:
        session_id (str, optional): Session. Defaults to None.
    """
    # make sure session id is availabe
    if not session_id:
        session_id = sessioninfo.get_session_uuid()

    hooks_handler = get_hooks_handler()
    if hooks_handler:
        # deactivate old
        hooks_handler.DeactivateEventHooks(uiApp=HOST_APP.uiapp)
    # setup new
    hooks_handler = EventHooks(session_id)
    set_hooks_handler(hooks_handler)
    unregister_all_hooks()
