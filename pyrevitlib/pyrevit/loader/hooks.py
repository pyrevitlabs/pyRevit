"""Hooks management."""
import os.path as op
import re
from collections import namedtuple

from pyrevit import HOST_APP
from pyrevit import framework
from pyrevit import coreutils
from pyrevit.coreutils.logger import get_logger
from pyrevit.coreutils import envvars
from pyrevit.runtime.types import EventHooks
import pyrevit.extensions as exts

from pyrevit.loader import sessioninfo


SUPPORTED_LANGUAGES = [
    exts.PYTHON_SCRIPT_FILE_FORMAT,
    exts.CSHARP_SCRIPT_FILE_FORMAT,
    exts.VB_SCRIPT_FILE_FORMAT,
    ]

#pylint: disable=W0703,C0302,C0103
mlogger = get_logger(__name__)


ExtensionEventHook = namedtuple('ExtensionEventHook', [
    'id',
    'name',
    'target',
    'script',
    'syspaths',
    'extension_name',
    ])


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


def is_valid_hook_script(hook_script):
    """Check if the given hook script is valid.

    Args:
        hook_script (str): hook script path

    Returns:
        (bool): True if the script is valid, False otherwise
    """
    return op.splitext(op.basename(hook_script))[1] in SUPPORTED_LANGUAGES


def _get_hook_parts(extension, hook_script):
    # finds the two parts of the hook script name
    # e.g command-before-exec[ID_INPLACE_COMPONENT].py
    # ('command-before-exec', 'ID_INPLACE_COMPONENT')
    parts = re.findall(
        r'([a-z -]+)\[?([A-Z _]+)?\]?\..+',
        op.basename(hook_script)
        )
    if parts:
        return parts[0]
    else:
        return '', ''


def _create_hook_id(extension, hook_script):
    hook_script_id = op.basename(hook_script)
    pieces = [extension.unique_name, hook_script_id]
    return coreutils.cleanup_string(
        exts.UNIQUE_ID_SEPARATOR.join(pieces),
        skip=[exts.UNIQUE_ID_SEPARATOR]
        ).lower()


def get_extension_hooks(extension):
    """Get the hooks of the given extension.

    Args:
        extension (pyrevit.extensions.components.Extension): pyRevit extension

    Returns:
        (list[ExtensionEventHook]): list of hooks
    """
    event_hooks = []
    for hook_script in extension.get_hooks():
        if is_valid_hook_script(hook_script):
            name, target = _get_hook_parts(extension, hook_script)
            if name:
                event_hooks.append(
                    ExtensionEventHook(
                        id=_create_hook_id(extension, hook_script),
                        name=name,
                        target=target,
                        script=hook_script,
                        syspaths=extension.module_paths,
                        extension_name=extension.name,
                    )
                )
    return event_hooks


def get_event_hooks():
    """Get all the event hooks."""
    hooks_handler = get_hooks_handler()
    return hooks_handler.GetAllEventHooks()


def register_hooks(extension):
    """Register the hooks for the given extension.

    Args:
        extension (pyrevit.extensions.components.Extension): pyRevit extension
    """
    hooks_handler = get_hooks_handler()
    for ext_hook in get_extension_hooks(extension):
        try:
            hooks_handler.RegisterHook(
                uniqueId=ext_hook.id,
                eventName=ext_hook.name,
                eventTarget=ext_hook.target,
                scriptPath=ext_hook.script,
                searchPaths=framework.Array[str](ext_hook.syspaths),
                extensionName=ext_hook.extension_name,
            )
        except Exception as hookEx:
            mlogger.error("Failed registering hook script %s | %s",
                          ext_hook.script, hookEx)


def unregister_hooks(extension):
    """Unregister all hooks for the given extension.

    Args:
        extension (pyrevit.extensions.components.Extension): pyRevit extension
    """
    hooks_handler = get_hooks_handler()
    for ext_hook in get_extension_hooks(extension):
        hooks_handler.UnRegisterHook(uniqueId=ext_hook.id)


def unregister_all_hooks():
    """Unregister all hooks."""
    hooks_handler = get_hooks_handler()
    hooks_handler.UnRegisterAllHooks(uiApp=HOST_APP.uiapp)


def activate():
    """Activate all event hooks."""
    hooks_handler = get_hooks_handler()
    hooks_handler.ActivateEventHooks(uiApp=HOST_APP.uiapp)


def deactivate():
    """Deactivate all event hooks."""
    hooks_handler = get_hooks_handler()
    hooks_handler.DeactivateEventHooks(uiApp=HOST_APP.uiapp)


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
