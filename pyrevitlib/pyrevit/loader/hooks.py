"""Hooks management."""
import os.path as op
from collections import namedtuple

from pyrevit import HOST_APP
from pyrevit import framework
from pyrevit import coreutils
from pyrevit.coreutils.logger import get_logger
from pyrevit.coreutils.loadertypes import EventUtils, PyRevitHooks
from pyrevit.coreutils import envvars
import pyrevit.extensions as exts

from pyrevit.loader import sessioninfo


#pylint: disable=W0703,C0302,C0103
mlogger = get_logger(__name__)


PYREVIT_HOOKS_ENVVAR = \
    envvars.PYREVIT_ENVVAR_PREFIX + '_HOOKS'
PYREVIT_HOOKSHANDLER_ENVVAR = \
    envvars.PYREVIT_ENVVAR_PREFIX + '_HOOKSHANDLER'


ExtensionEventHook = namedtuple('ExtensionEventHook', [
    'id',
    'name',
    'script',
    'syspaths',
    'extension_name',
    ])


def get_hooks_handler():
    return envvars.get_pyrevit_env_var(PYREVIT_HOOKSHANDLER_ENVVAR)


def set_hooks_handler(handler):
    envvars.set_pyrevit_env_var(PYREVIT_HOOKSHANDLER_ENVVAR, handler)


def _create_hook_id(extension, hook_script):
    hook_script_id = op.basename(hook_script)
    pieces = [extension.unique_name, hook_script_id]
    return coreutils.cleanup_string(
        exts.UNIQUE_ID_SEPARATOR.join(pieces),
        skip=[exts.UNIQUE_ID_SEPARATOR]
        ).lower()


def get_extension_hooks(extension):
    event_hooks = []
    for hook_script in extension.get_hooks():
        event_hooks.append(
            ExtensionEventHook(
                id=_create_hook_id(extension, hook_script),
                name=op.splitext(op.basename(hook_script))[0].lower(),
                script=hook_script,
                syspaths=extension.module_paths,
                extension_name=extension.name,
            )
        )
    return event_hooks


def get_event_hooks():
    hooks_handler = get_hooks_handler()
    return hooks_handler.GetAllEventHooks()


def register_hooks(extension):
    hooks_handler = get_hooks_handler()
    for ext_hook in get_extension_hooks(extension):
        hooks_handler.RegisterHook(
            uniqueId=ext_hook.id,
            eventName=ext_hook.name,
            scriptPath=ext_hook.script,
            searchPaths=framework.Array[str](ext_hook.syspaths),
            extensionName=ext_hook.extension_name,
        )


def unregister_hooks(extension):
    hooks_handler = get_hooks_handler()
    for ext_hook in get_extension_hooks(extension):
        hooks_handler.UnRegisterHook(uniqueId=ext_hook.id)


def unregister_all_hooks():
    hooks_handler = get_hooks_handler()
    hooks_handler.UnRegisterAllHooks(uiApp=HOST_APP.uiapp)


def activate():
    hooks_handler = get_hooks_handler()
    hooks_handler.ActivateEventHooks(uiApp=HOST_APP.uiapp)


def deactivate():
    hooks_handler = get_hooks_handler()
    hooks_handler.DeactivateEventHooks(uiApp=HOST_APP.uiapp)


def setup_hooks(session_id=None):
    # make sure session id is availabe
    if not session_id:
        session_id = sessioninfo.get_session_uuid()

    hooks_handler = get_hooks_handler()
    if hooks_handler:
        # deactivate old
        hooks_handler.DeactivateAllEventHooks(uiApp=HOST_APP.uiapp)
    # setup new
    hooks_handler = PyRevitHooks(session_id)
    set_hooks_handler(hooks_handler)
    unregister_all_hooks()
