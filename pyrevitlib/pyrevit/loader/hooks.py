"""Hooks management."""
import os.path as op
from collections import namedtuple

from pyrevit import HOST_APP
from pyrevit import framework
from pyrevit import coreutils
from pyrevit.coreutils.loadertypes import EventUtils, PyRevitHooks
from pyrevit.coreutils import envvars
import pyrevit.extensions as exts


PYREVIT_HOOKS_ENVVAR = \
    envvars.PYREVIT_ENVVAR_PREFIX + '_HOOKS'


PYREVIT_HOOKS = PyRevitHooks()


EventHook = namedtuple('EventHook', [
    'script',
    'event_type',
    'syspaths',
    'extension_name',
    'id',
    ])


def _create_hook_id(extension, hook_script):
    hook_script_id = op.basename(hook_script)
    pieces = [extension.unique_name, hook_script_id]
    return coreutils.cleanup_string(
        exts.UNIQUE_ID_SEPARATOR.join(pieces),
        skip=[exts.UNIQUE_ID_SEPARATOR]
        ).lower()


def get_hook_script_type(hook_script):
    hook_name = op.splitext(op.basename(hook_script))[0].lower()
    return EventUtils.GetEventType(hook_name)


def get_extension_hooks(extension):
    event_hooks = []
    for hook_script in extension.get_hooks():
        hook_type = get_hook_script_type(hook_script)
        # hook_type is a C# enum and first item is 0 == False
        # check for nullness
        if hook_type is not None:
            event_hooks.append(
                EventHook(
                    script=hook_script,
                    event_type=hook_type,
                    syspaths=extension.module_paths,
                    extension_name=extension.name,
                    id=_create_hook_id(extension, hook_script)
                )
            )
    return event_hooks


def get_active_hooks():
    return PYREVIT_HOOKS


def get_all_active_hooks():
    return [PYREVIT_HOOKS]


def get_event_hooks():
    active_hooks = get_active_hooks()
    return active_hooks.GetAllEventHooks()


def register_hooks(extension):
    active_hooks = get_active_hooks()
    for ext_hook in get_extension_hooks(extension):
        active_hooks.RegisterHook(
            uiApp=HOST_APP.uiapp,
            script=ext_hook.script,
            eventType=ext_hook.event_type,
            searchPaths=framework.Array[str](ext_hook.syspaths),
            extName=ext_hook.extension_name,
            uniqueId=ext_hook.id
        )


def unregister_hooks(extension):
    for ext_hook in get_extension_hooks(extension):
        PyRevitHooks.UnRegisterHook(
            uiApp=HOST_APP.uiapp,
            script=ext_hook.script,
            eventType=ext_hook.event_type,
            searchPaths=framework.Array[str](ext_hook.syspaths),
            extName=ext_hook.extension_name,
            uniqueId=ext_hook.id
        )


def unregister_all_hooks():
    active_hooks = get_active_hooks()
    active_hooks.UnRegisterAllHooks(uiApp=HOST_APP.uiapp)


def activate():
    active_hooks = get_active_hooks()
    active_hooks.ActivateEventHooks(uiApp=HOST_APP.uiapp)


def deactivate():
    for active_hooks in get_all_active_hooks():
        active_hooks.DeactivateEventHooks(uiApp=HOST_APP.uiapp)
