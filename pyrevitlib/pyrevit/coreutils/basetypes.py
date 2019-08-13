"""Provide access to classes and functionalty inside base loader module."""

from pyrevit import EXEC_PARAMS
from pyrevit.framework import clr
from pyrevit.loader.basetypes import BASE_TYPES_ASM, BASE_NAMESPACE

#pylint: disable=W0703,C0302,C0103
if not EXEC_PARAMS.doc_mode:
    # import base classes module
    clr.AddReference(BASE_TYPES_ASM)
    base_module = __import__(BASE_NAMESPACE)

    # envvars.cs
    DomainStorageKeys = base_module.DomainStorageKeys
    EnvDictionaryKeys = base_module.EnvDictionaryKeys
    EnvDictionary = base_module.EnvDictionary

    # baseclasses.cs
    CommandType = base_module.CommandType
    CommandExtendedAvail = base_module.CommandExtendedAvail
    CommandSelectionAvail = base_module.CommandSelectionAvail
    CommandZeroDocAvail = base_module.CommandZeroDocAvail

    # pyrevitcmdruntime.cs
    ScriptRuntime = base_module.ScriptRuntime

    # executor.cs
    ExecutionResultCodes = base_module.ExecutionResultCodes
    ExecutionConfigs = base_module.ExecutionConfigs
    ScriptExecutor = base_module.ScriptExecutor

    # events.cs
    EventUtils = base_module.EventUtils
    AppEventUtils = base_module.AppEventUtils
    UIEventUtils = base_module.UIEventUtils
    PlaceKeynoteExternalEventHandler = \
        base_module.PlaceKeynoteExternalEventHandler

    # hooks.cs
    EventHook = base_module.EventHook
    PyRevitHooks = base_module.PyRevitHooks

    # scriptoutput.cs
    ScriptOutputConfigs = base_module.ScriptOutputConfigs
    PyRevitTemplateWindow = base_module.PyRevitTemplateWindow
    ScriptOutput = base_module.ScriptOutput
    # scriptoutputemojis.cs
    ScriptOutputEmojis = base_module.ScriptOutputEmojis
    # scriptoutputmgr.cs
    ScriptOutputManager = base_module.ScriptOutputManager
    # scriptoutputstream.cs
    ScriptOutputStream = base_module.ScriptOutputStream

    # telemetry.cs
    EventType = base_module.EventType
    ScriptTelemetry = base_module.ScriptTelemetry
    EventTelemetry = base_module.EventTelemetry

    # unmanaged.cs
    RECT = base_module.RECT
    User32 = base_module.User32
    GDI32 = base_module.GDI32
else:
    DomainStorageKeys = ExternalConfig = ExecutionResultCodes = \
        EnvDictionaryKeys = EnvDictionary = CommandType = \
        CommandExtendedAvail = CommandSelectionAvail = \
        CommandDefaultAvail = ScriptRuntime = \
        ScriptExecutor = ScriptOutput = ScriptOutputManager = \
        ScriptOutputStream = ScriptTelemetry = \
        RECT = User32 = GDI32 = None
