from pyrevit.framework import clr
from pyrevit.loader.basetypes import BASE_TYPES_ASM, LOADER_BASE_NAMESPACE


# import base classes module
clr.AddReference(BASE_TYPES_ASM)
base_module = __import__(LOADER_BASE_NAMESPACE)

ExternalConfig = base_module.ExternalConfig
ExecutionErrorCodes = base_module.ExecutionErrorCodes
EnvDictionaryKeys = base_module.EnvDictionaryKeys
PyRevitCommand = base_module.PyRevitCommand
PyRevitCommandCategoryAvail = base_module.PyRevitCommandCategoryAvail
PyRevitCommandSelectionAvail = base_module.PyRevitCommandSelectionAvail
PyRevitCommandDefaultAvail = base_module.PyRevitCommandDefaultAvail
ScriptExecutor = base_module.ScriptExecutor
ScriptOutput = base_module.ScriptOutput
ScriptOutputStream = base_module.ScriptOutputStream
ScriptUsageLogger = base_module.ScriptUsageLogger
