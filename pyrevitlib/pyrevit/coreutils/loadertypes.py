"""Provide access to classes and functionalty inside base loader module."""

from pyrevit import EXEC_PARAMS
from pyrevit.framework import clr
from pyrevit.loader.basetypes import BASE_TYPES_ASM, LOADER_BASE_NAMESPACE

#pylint: disable=W0703,C0302,C0103
if not EXEC_PARAMS.doc_mode:
    # import base classes module
    clr.AddReference(BASE_TYPES_ASM)
    base_module = __import__(LOADER_BASE_NAMESPACE)

    # _config.cs
    DomainStorageKeys = base_module.DomainStorageKeys
    ExternalConfig = base_module.ExternalConfig
    ExecutionErrorCodes = base_module.ExecutionErrorCodes

    # envvars.cs
    EnvDictionaryKeys = base_module.EnvDictionaryKeys
    EnvDictionary = base_module.EnvDictionary

    # baseclasses.cs
    PyRevitCommand = base_module.PyRevitCommand
    PyRevitCommandExtendedAvail = base_module.PyRevitCommandExtendedAvail
    PyRevitCommandSelectionAvail = base_module.PyRevitCommandSelectionAvail
    PyRevitCommandDefaultAvail = base_module.PyRevitCommandDefaultAvail

    # pyrevitcmdruntime.cs
    PyRevitCommandRuntime = base_module.PyRevitCommandRuntime

    # executor.cs
    ScriptExecutor = base_module.ScriptExecutor

    # helpers.cs
    UIDocUtils = base_module.UIDocUtils

    # scriptoutput.cs
    PyRevitTemplateWindow = base_module.PyRevitTemplateWindow
    ScriptOutput = base_module.ScriptOutput
    # scriptoutputemojis.cs
    ScriptOutputEmojis = base_module.ScriptOutputEmojis
    # scriptoutputmgr.cs
    ScriptOutputManager = base_module.ScriptOutputManager
    # scriptoutputstream.cs
    ScriptOutputStream = base_module.ScriptOutputStream

    # usagelogger.cs
    ScriptUsageLogger = base_module.ScriptUsageLogger

    # unmanaged.cs
    RECT = base_module.RECT
    User32 = base_module.User32
    GDI32 = base_module.GDI32
else:
    DomainStorageKeys = ExternalConfig = ExecutionErrorCodes = \
        EnvDictionaryKeys = EnvDictionary = PyRevitCommand = \
        PyRevitCommandExtendedAvail = PyRevitCommandSelectionAvail = \
        PyRevitCommandDefaultAvail = PyRevitCommandRuntime = \
        ScriptExecutor = ScriptOutput = ScriptOutputManager = \
        ScriptOutputStream = ScriptUsageLogger = \
        RECT = User32 = GDI32 = None
