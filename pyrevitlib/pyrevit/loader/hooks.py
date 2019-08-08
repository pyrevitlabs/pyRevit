"""Hooks management."""
import os.path as op
from collections import namedtuple

from pyrevit import HOST_APP
from pyrevit import framework
from pyrevit import coreutils
from pyrevit.coreutils.loadertypes import EventType, PyRevitHooks
from pyrevit.coreutils import envvars
import pyrevit.extensions as exts


PYREVIT_HOOKS_ENVVAR = \
    envvars.PYREVIT_ENVVAR_PREFIX + '_HOOKS'


HOOK_TYPES = {
    'app-closing': EventType.UIApplication_ApplicationClosing,
    'app-idling': EventType.UIApplication_Idling,
    'app-init': EventType.Application_ApplicationInitialized,
    'dialog-showing': EventType.UIApplication_DialogBoxShowing,
    'doc-changed': EventType.Application_DocumentChanged,
    'doc-closed': EventType.Application_DocumentClosed,
    'doc-closing': EventType.Application_DocumentClosing,
    'doc-created': EventType.Application_DocumentCreated,
    'doc-creating': EventType.Application_DocumentCreating,
    'doc-opened': EventType.Application_DocumentOpened,
    'doc-opening': EventType.Application_DocumentOpening,
    'doc-printed': EventType.Application_DocumentPrinted,
    'doc-printing': EventType.Application_DocumentPrinting,
    'doc-saved-as': EventType.Application_DocumentSavedAs,
    'doc-saved': EventType.Application_DocumentSaved,
    'doc-saving-as': EventType.Application_DocumentSavingAs,
    'doc-saving': EventType.Application_DocumentSaving,
    'doc-synced': EventType.Application_DocumentSynchronizedWithCentral,
    'doc-syncing': EventType.Application_DocumentSynchronizingWithCentral,
    'doc-worksharing-enabled': EventType.Application_DocumentWorksharingEnabled,
    'dock-focus-changed': EventType.UIApplication_DockableFrameFocusChanged,
    'dock-visibility-changed':
        EventType.UIApplication_DockableFrameVisibilityChanged,
    'fabparts-browser-changed':
        EventType.UIApplication_FabricationPartBrowserChanged,
    'failure-processing': EventType.Application_FailuresProcessing,
    'family-loaded': EventType.Application_FamilyLoadedIntoDocument,
    'family-loading': EventType.Application_FamilyLoadingIntoDocument,
    'file-exported': EventType.Application_FileExported,
    'file-exporting': EventType.Application_FileExporting,
    'file-imported': EventType.Application_FileImported,
    'file-importing': EventType.Application_FileImporting,
    'formula-editing': EventType.UIApplication_FormulaEditing,
    'link-opened': EventType.Application_LinkedResourceOpened,
    'link-opening': EventType.Application_LinkedResourceOpening,
    'options-showing': EventType.UIApplication_DisplayingOptionsDialog,
    'progress-changed': EventType.Application_ProgressChanged,
    'transferred_project_standards':
        EventType.UIApplication_TransferredProjectStandards,
    'transferring_project_standards':
        EventType.UIApplication_TransferringProjectStandards,
    'type-duplicated': EventType.Application_ElementTypeDuplicated,
    'type-duplicating': EventType.Application_ElementTypeDuplicating,
    'view-activated': EventType.UIApplication_ViewActivated,
    'view-activating': EventType.UIApplication_ViewActivating,
    'view-exported': EventType.Application_ViewExported,
    'view-exporting': EventType.Application_ViewExporting,
    'view-printed': EventType.Application_ViewPrinted,
    'view-printing': EventType.Application_ViewPrinting,
    'worksharing-ops-progress-changed':
        EventType.Application_WorksharedOperationProgressChanged,
}


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
    hook_script_name = op.splitext(op.basename(hook_script))[0].lower()
    for hook_type in HOOK_TYPES:
        if hook_script_name == hook_type:
            return HOOK_TYPES[hook_type]


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


def get_event_hooks():
    return PyRevitHooks.GetAllEventHooks()


def register_hooks(extension):
    for ext_hook in get_extension_hooks(extension):
        PyRevitHooks.RegisterHook(
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
    PyRevitHooks.UnRegisterAllHooks(uiApp=HOST_APP.uiapp)


def activate():
    PyRevitHooks.ActivateEventHooks(uiApp=HOST_APP.uiapp)


def deactivate():
    PyRevitHooks.DeactivateEventHooks(uiApp=HOST_APP.uiapp)
