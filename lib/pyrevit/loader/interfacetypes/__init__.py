import os
import os.path as op
import sys

import clr
from Autodesk.Revit.Attributes import RegenerationAttribute, RegenerationOption, TransactionAttribute, TransactionMode
from System import Array, Type
from System.Reflection import TypeAttributes, MethodAttributes, CallingConventions
from System.Reflection.Emit import CustomAttributeBuilder, OpCodes

from pyrevit.core.exceptions import PyRevitException
from pyrevit.coreutils import make_canonical_name, find_loaded_asm, load_asm_file, calculate_dir_hash
from pyrevit.coreutils.appdata import PYREVIT_APP_DIR, get_data_file, is_data_file_available
from pyrevit.coreutils.dotnetcompiler import compile_csharp
from pyrevit.coreutils.logger import get_logger
from pyrevit.loader import ASSEMBLY_FILE_TYPE

logger = get_logger(__name__)


# folders --------------------------------------------------------------------------------------------------------------
LOADER_DIR = op.dirname(op.dirname(__file__))
ADDIN_DIR = op.join(LOADER_DIR, 'addin')

sys.path.append(ADDIN_DIR)
sys.path.append(PYREVIT_APP_DIR)

ADDIN_RESOURCE_DIR = op.join(ADDIN_DIR, 'Source', 'pyRevitLoader', 'Resources')
INTERFACE_TYPES_DIR = op.join(LOADER_DIR, 'interfacetypes')

DOTNET_SDK_DIR = op.join(os.getenv('programfiles(x86)'),
                         'Reference Assemblies', 'Microsoft', 'Framework', '.NETFramework')

FRAMEWORK_DIRS = os.listdir(DOTNET_SDK_DIR)


# base classes for pyRevit commands ------------------------------------------------------------------------------------
LOADER_BASE_NAMESPACE = 'PyRevitBaseClasses'

# template python command class
CMD_EXECUTOR_CLASS_NAME = '{}.{}'.format(LOADER_BASE_NAMESPACE, 'PyRevitCommand')

# template python command availability class
CMD_AVAIL_CLS_NAME = make_canonical_name(LOADER_BASE_NAMESPACE, 'PyRevitCommandDefaultAvail')
CMD_AVAIL_CLS_NAME_CATEGORY = make_canonical_name(LOADER_BASE_NAMESPACE, 'PyRevitCommandCategoryAvail')
CMD_AVAIL_CLS_NAME_SELECTION = make_canonical_name(LOADER_BASE_NAMESPACE, 'PyRevitCommandSelectionAvail')

source_file_filter = '(\.cs)'
BASE_CLASSES_ASM_FILE_ID = '{}_{}'.format(calculate_dir_hash(INTERFACE_TYPES_DIR, '', source_file_filter),
                                          LOADER_BASE_NAMESPACE)
BASE_CLASSES_ASM_FILE = get_data_file(BASE_CLASSES_ASM_FILE_ID, ASSEMBLY_FILE_TYPE)
# taking the name of the generated data file and use it as assembly name
BASE_CLASSES_ASM_NAME = op.splitext(op.basename(BASE_CLASSES_ASM_FILE))[0]
logger.debug('Interface types assembly file is: {}'.format(BASE_CLASSES_ASM_NAME))


def _get_source_files():
    source_files = list()
    source_dir = op.dirname(__file__)
    logger.debug('Source files location: {}'.format(source_dir))
    for source_file in os.listdir(source_dir):
        if op.splitext(source_file)[1].lower() == '.cs':
            logger.debug('Source file found: {}'.format(source_file))
            source_files.append(op.join(source_dir, source_file))

    logger.debug('Source files to be compiled: {}'.format(source_files))
    return source_files


def _get_resource_file(resource_name):
    return op.join(ADDIN_RESOURCE_DIR, resource_name)


def _get_framework_module(fw_module):
    # start with the newest sdk folder and work backwards trying to find the dll
    for sdk_folder in reversed(FRAMEWORK_DIRS):
        fw_module_file = op.join(DOTNET_SDK_DIR, sdk_folder, make_canonical_name(fw_module, ASSEMBLY_FILE_TYPE))
        if op.exists(fw_module_file):
            sys.path.append(op.join(DOTNET_SDK_DIR, sdk_folder))
            return fw_module_file

    return None


def _get_addin_dll_file(addin_filename):
    addin_file = op.join(ADDIN_DIR, make_canonical_name(addin_filename, ASSEMBLY_FILE_TYPE))
    if op.exists(addin_file):
        return addin_file

    return None


def _get_reference_file(ref_name):
    # First try to find the dll in the project folder
    addin_file = _get_addin_dll_file(ref_name)
    if addin_file:
        return addin_file

    # Then try to find the dll in windows SDK
    fw_module_file = _get_framework_module(ref_name)
    if fw_module_file:
        return fw_module_file

    # Lastly try to find location of assembly if already loaded
    loaded_asm = find_loaded_asm(ref_name)
    if loaded_asm:
        return loaded_asm.Location

    # if not worked raise critical error
    logger.critical('Can not find required reference assembly: {}'.format(ref_name))


def _get_references():
    ref_list = ['RevitAPI', 'RevitAPIUI', 'IronPython', 'IronPython.Modules',
                'Microsoft.Dynamic', 'Microsoft.Scripting', 'Microsoft.CSharp',
                'System', 'System.Core', 'System.Drawing', 'System.Windows.Forms',
                'PresentationCore', 'PresentationFramework', 'WindowsBase']

    return [_get_reference_file(ref_name) for ref_name in ref_list]


def _generate_base_classes_asm():
    source_list = list()
    for source_file in _get_source_files():
        # fixme: handle read errors
        with open(source_file, 'r') as code_file:
            source_list.append(code_file.read())
    try:
        logger.debug('Compiling interface types to: {}'.format(BASE_CLASSES_ASM_FILE))
        compile_csharp(source_list, BASE_CLASSES_ASM_FILE,
                       reference_list=_get_references(), resource_list=[_get_resource_file('python_27_lib.zip')])
        return load_asm_file(BASE_CLASSES_ASM_FILE)

    except PyRevitException as compile_err:
        logger.critical('Can not compile interface types code into assembly. | {}'.format(compile_err))
        raise compile_err


def _get_base_classes_asm():
    if is_data_file_available(file_id=BASE_CLASSES_ASM_FILE_ID, file_ext=ASSEMBLY_FILE_TYPE):
        return load_asm_file(BASE_CLASSES_ASM_FILE)
    else:
        return _generate_base_classes_asm()


def _find_pyrevit_base_class(base_class_name):
    base_class = BASE_CLASSES_ASM.GetType(base_class_name)
    if base_class is not None:
        logger.debug('Base class type found: {}'.format(base_class))
        return base_class
    else:
        raise PyRevitException('Can not find base class type: {}'.format(base_class_name))


# see it the assembly is already loaded
BASE_CLASSES_ASM = find_loaded_asm(BASE_CLASSES_ASM_NAME)
# else, let's generate the assembly and load it
if not BASE_CLASSES_ASM:
    BASE_CLASSES_ASM = _get_base_classes_asm()


CMD_EXECUTOR_CLASS = _find_pyrevit_base_class(CMD_EXECUTOR_CLASS_NAME)
CMD_AVAIL_CLS = _find_pyrevit_base_class(CMD_AVAIL_CLS_NAME)
CMD_AVAIL_CLS_CATEGORY = _find_pyrevit_base_class(CMD_AVAIL_CLS_NAME_CATEGORY)
CMD_AVAIL_CLS_SELECTION = _find_pyrevit_base_class(CMD_AVAIL_CLS_NAME_SELECTION)


def _create_base_type(modulebuilder, type_class, class_name, custom_attr_list, *args):
    # create type builder
    type_builder = modulebuilder.DefineType(class_name, TypeAttributes.Class | TypeAttributes.Public, type_class)

    for custom_attr in custom_attr_list:
        type_builder.SetCustomAttribute(custom_attr)

    # prepare a list of input param types to find the matching constructor
    type_list = []
    param_list = []
    for param in args:
        if type(param) == str:
            type_list.append(type(param))
            param_list.append(param)

    # call base constructor
    ci = type_class.GetConstructor(Array[Type](type_list))
    # create class constructor builder
    const_builder = type_builder.DefineConstructor(MethodAttributes.Public,
                                                   CallingConventions.Standard,
                                                   Array[Type](()))
    # add constructor parameters to stack
    gen = const_builder.GetILGenerator()
    gen.Emit(OpCodes.Ldarg_0)  # Load "this" onto eval stack

    # add constructor input params to the stack
    for param in param_list:
        gen.Emit(OpCodes.Ldstr, param)

    gen.Emit(OpCodes.Call, ci)  # call base constructor (consumes "this" and the created stack)
    gen.Emit(OpCodes.Nop)  # Fill some space - this is how it is generated for equivalent C# code
    gen.Emit(OpCodes.Nop)
    gen.Emit(OpCodes.Nop)
    gen.Emit(OpCodes.Ret)
    type_builder.CreateType()


def _create_cmd_avail_type(module_builder, cmd_params):
    """

    Args:
        module_builder:
        cmd_params (pyrevit.loader.asmmaker.CommandExecutorParams):

    Returns:

    """
    logger.debug('Creating availability type for: {}'.format(cmd_params))
    if cmd_params.cmd_context == 'Selection':
        _create_base_type(module_builder, CMD_AVAIL_CLS_SELECTION,
                          cmd_params.avail_class_name, [], cmd_params.cmd_context)
    else:
        _create_base_type(module_builder, CMD_AVAIL_CLS_CATEGORY,
                          cmd_params.avail_class_name, [], cmd_params.cmd_context)


def _create_cmd_loader_type(module_builder, cmd_params):
    """

    Args:
        module_builder:
        cmd_params (CommandExecutorParams):

    Returns:

    """
    logger.debug('Creating loader class type for: {}'.format(cmd_params))

    # add RegenerationAttribute to type
    regen_const_info = clr.GetClrType(RegenerationAttribute).GetConstructor(Array[Type]((RegenerationOption,)))
    regen_attr_builder = CustomAttributeBuilder(regen_const_info,
                                                Array[object]((RegenerationOption.Manual,)))
    # add TransactionAttribute to type
    trans_constructor_info = clr.GetClrType(TransactionAttribute).GetConstructor(Array[Type]((TransactionMode,)))
    trans_attrib_builder = CustomAttributeBuilder(trans_constructor_info,
                                                  Array[object]((TransactionMode.Manual,)))

    _create_base_type(module_builder, CMD_EXECUTOR_CLASS, cmd_params.class_name,
                      [regen_attr_builder, trans_attrib_builder],
                      cmd_params.script_file_address,
                      cmd_params.config_script_file_address,
                      cmd_params.log_file,
                      cmd_params.search_paths_str,
                      cmd_params.cmd_name,
                      cmd_params.cmd_options)


# public base class maker function -------------------------------------------------------------------------------------
def make_cmd_classes(module_builder, cmd_params):
    # make command interface type for the given command
    _create_cmd_loader_type(module_builder, cmd_params)

    # create command availability class for this command
    if cmd_params.avail_class_name:
        _create_cmd_avail_type(module_builder, cmd_params)


def make_shared_classes(module_builder):
    _create_base_type(module_builder, CMD_AVAIL_CLS, CMD_AVAIL_CLS_NAME, [])
