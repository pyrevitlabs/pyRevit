"""Provide access to classes and functionalty inside base loader module."""

from pyrevit import EXEC_PARAMS
import pyrevit.compat as compat
from pyrevit.framework import clr
from pyrevit.runtime import RUNTIME_ASSM, RUNTIME_NAMESPACE

#pylint: disable=W0703,C0302,C0103
if not EXEC_PARAMS.doc_mode:
    # import base classes module
    if compat.PY3:
        clr.AddReference(RUNTIME_ASSM.Location)
    else:
        clr.AddReference(RUNTIME_ASSM)

    # The __import__ function will return the top level module of a package,
    # unless you pass a nonempty fromlist argument
    runtime_module = __import__(RUNTIME_NAMESPACE, fromlist=['object'])
    if compat.PY3:
        runtime_module = runtime_module.PyRevit.Runtime

    # envvars.cs
    DomainStorageKeys = runtime_module.DomainStorageKeys
    EnvDictionaryKeys = runtime_module.EnvDictionaryKeys
    EnvDictionary = runtime_module.EnvDictionary

    # baseclasses.cs
    CommandType = runtime_module.CommandType
    CommandTypeExecConfigs = runtime_module.CommandTypeExecConfigs
    CommandExtendedAvail = runtime_module.CommandExtendedAvail
    CommandSelectionAvail = runtime_module.CommandSelectionAvail
    CommandZeroDocAvail = runtime_module.CommandZeroDocAvail

    # enginemgr.cs
    EngineType = runtime_module.EngineType
    ExecutionEngineConfigs = runtime_module.ExecutionEngineConfigs
    IronPythonEngineConfigs = runtime_module.IronPythonEngineConfigs
    ExecutionEngine = runtime_module.ExecutionEngine
    EngineManager = runtime_module.EngineManager
    IronPythonEngine = runtime_module.IronPythonEngine

    # scriptruntime.cs
    ScriptData = runtime_module.ScriptData
    ScriptRuntimeConfigs = runtime_module.ScriptRuntimeConfigs
    ScriptRuntime = runtime_module.ScriptRuntime

    # executor.cs
    ExecutionResultCodes = runtime_module.ExecutionResultCodes
    ScriptExecutor = runtime_module.ScriptExecutor

    # events.cs
    EventUtils = runtime_module.EventUtils
    AppEventUtils = runtime_module.AppEventUtils
    UIEventUtils = runtime_module.UIEventUtils
    PlaceKeynoteExternalEventHandler = \
        runtime_module.PlaceKeynoteExternalEventHandler

    # hooks.cs
    EventHook = runtime_module.EventHook
    PyRevitHooks = runtime_module.PyRevitHooks

    # scriptoutput.cs
    ScriptOutputConfigs = runtime_module.ScriptOutputConfigs
    PyRevitTemplateWindow = runtime_module.PyRevitTemplateWindow
    ScriptOutput = runtime_module.ScriptOutput
    # scriptoutputemojis.cs
    ScriptOutputEmojis = runtime_module.ScriptOutputEmojis
    # scriptoutputmgr.cs
    ScriptOutputManager = runtime_module.ScriptOutputManager
    # scriptoutputstream.cs
    ScriptOutputStream = runtime_module.ScriptOutputStream

    # telemetry.cs
    EventType = runtime_module.EventType
    ScriptTelemetry = runtime_module.ScriptTelemetry
    EventTelemetry = runtime_module.EventTelemetry
else:
    DomainStorageKeys = ExternalConfig = ExecutionResultCodes = \
        EnvDictionaryKeys = EnvDictionary = CommandType = \
        CommandExtendedAvail = CommandSelectionAvail = \
        CommandDefaultAvail = ScriptRuntime = \
        ScriptExecutor = ScriptOutput = ScriptOutputManager = \
        ScriptOutputStream = ScriptTelemetry = None
