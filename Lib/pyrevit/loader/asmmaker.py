import os
import os.path as op
from collections import namedtuple

import clr
from pyrevit.coreutils.coreutils import join_strings, get_revit_instances

from pyrevit.config import PyRevitVersion, USER_TEMP_DIR
from ..core.exceptions import PyRevitException
from ..core.logger import get_logger

clr.AddReference('PresentationCore')
clr.AddReference('RevitAPI')
clr.AddReference('RevitAPIUI')
clr.AddReference('System.Xml.Linq')

# noinspection PyUnresolvedReferences
from System import AppDomain, Version, Array, Type
# noinspection PyUnresolvedReferences
from System.Reflection import Assembly, AssemblyName, TypeAttributes, MethodAttributes, CallingConventions
# noinspection PyUnresolvedReferences
from System.Reflection.Emit import AssemblyBuilderAccess, CustomAttributeBuilder, OpCodes
# noinspection PyUnresolvedReferences
from Autodesk.Revit.Attributes import RegenerationAttribute, RegenerationOption, TransactionAttribute, TransactionMode

logger = get_logger(__name__)


# ----------------------------------------------------------------------------------------------------------------------
# asm maker defaults
# ----------------------------------------------------------------------------------------------------------------------
ASSEMBLY_FILE_TYPE = '.dll'
LOADER_ADDIN = 'PyRevitLoader'

# template python command class
LOADER_BASE_CLASSES_ASM = 'PyRevitBaseClasses'
LOADER_ADDIN_COMMAND_INTERFACE_CLASS_EXT = '{}.{}'.format(LOADER_BASE_CLASSES_ASM, 'PyRevitCommand')

# template python command availability class
LOADER_ADDIN_COMMAND_DEFAULT_AVAIL_CLASS_NAME = 'PyRevitCommandDefaultAvail'
LOADER_ADDIN_COMMAND_DEFAULT_AVAIL_CLASS = '{}.{}'.format(LOADER_BASE_CLASSES_ASM,
                                                          LOADER_ADDIN_COMMAND_DEFAULT_AVAIL_CLASS_NAME)
LOADER_ADDIN_COMMAND_CAT_AVAIL_CLASS = '{}.{}'.format(LOADER_BASE_CLASSES_ASM, 'PyRevitCommandCategoryAvail')
LOADER_ADDIN_COMMAND_SEL_AVAIL_CLASS = '{}.{}'.format(LOADER_BASE_CLASSES_ASM, 'PyRevitCommandSelectionAvail')




# Generic named tuple for passing assembly information to other modules
PackageAssemblyInfo = namedtuple('PackageAssemblyInfo', ['name', 'location', 'reloading'])

# Generic named tuple for passing loader class parameters to the assembly maker
LoaderClassParams = namedtuple('LoaderClassParams',
                               ['class_name',
                                'avail_class_name',
                                'script_file_address', 'config_script_file_address',
                                'search_paths_str',
                                'cmd_name',
                                'cmd_context'
                                ])


def _make_baseclasses_asm_name():
    return SESSION_STAMPED_ID + '_' + LOADER_BASE_CLASSES_ASM


def _make_pkg_asm_name(pkg):
    return SESSION_ID + '_' + pkg.hash_value + '_' + pkg.unique_name


def _generate_base_classes_asm():
    with open(op.join(LOADER_DIR, 'lib', 'pyrevit', 'loader', 'cstemplates','baseclasses.cs'), 'r') as code_file:
        source = code_file.read()
    try:
        baseclass_asm = compile_to_asm(source, _make_baseclasses_asm_name(), USER_TEMP_DIR,
                                       references=[_find_loaded_asm('PresentationCore').Location,
                                                   _find_loaded_asm('WindowsBase').Location,
                                                   'RevitAPI.dll', 'RevitAPIUI.dll',
                                                   op.join(LOADER_ASM_DIR, LOADER_ADDIN + ASSEMBLY_FILE_TYPE)])
    except PyRevitException as compile_err:
        logger.critical('Can not compile cstemplates code into assembly. | {}'.format(compile_err))
        raise compile_err

    return Assembly.LoadFrom(baseclass_asm)


def _load_asm_file(asm_file):
    return Assembly.LoadFile(asm_file)


def _find_loaded_asm(asm_name):
    logger.debug('Asking Revit for loaded assembly: {}'.format(asm_name))
    loaded_asm_list = []
    for loaded_assembly in AppDomain.CurrentDomain.GetAssemblies():
        if asm_name.lower() == str(loaded_assembly.GetName().Name).lower():
            logger.debug('Assembly found: {0}'.format(loaded_assembly.GetName().FullName))
            loaded_asm_list.append(loaded_assembly)

    count = len(loaded_asm_list)
    if count == 0:
        return None
    elif count == 1:
        return loaded_asm_list[0]
    elif count > 1:
        return loaded_asm_list


def _find_base_classes_asm():
    base_classes_asm = _find_loaded_asm(_make_baseclasses_asm_name())
    if base_classes_asm is not None:
        return base_classes_asm
    else:
        # if base classes is not already loaded, compile_to_asm and load the assembly
        return _generate_base_classes_asm()


def _find_pyrevit_base_class(base_class_name):
    baseclass_asm = _find_base_classes_asm()
    base_class = baseclass_asm.GetType(base_class_name)
    if base_class is not None:
        return base_class
    else:
        raise PyRevitException('Can not find base class type: {}'.format(base_class_name))


def _get_params_for_commands(parent_cmp):
    loader_params_for_all_cmds = []

    logger.debug('Creating a list of commands for the assembly maker from: {}'.format(parent_cmp))
    for sub_cmp in parent_cmp:
        if sub_cmp.is_container():
            loader_params_for_all_cmds.extend(_get_params_for_commands(sub_cmp))
        else:
            try:
                logger.debug('Command found: {}'.format(sub_cmp))
                loader_params_for_all_cmds.append(LoaderClassParams(sub_cmp.unique_name,
                                                                    sub_cmp.unique_avail_name,
                                                                    sub_cmp.get_full_script_address(),
                                                                    sub_cmp.get_full_config_script_address(),
                                                                    join_strings(sub_cmp.get_search_paths()),
                                                                    sub_cmp.name,
                                                                    join_strings(sub_cmp.get_cmd_options()),
                                                                    sub_cmp.cmd_context
                                                                    ))
            except Exception as err:
                logger.debug('Can not create class parameters from: {} | {}'.format(sub_cmp, err))

    return loader_params_for_all_cmds


def _is_pyrevit_asm_file(file_name):
    # if this is a pyRevit assembly file
    return (file_name.startswith(SESSION_ID) and file_name.endswith(ASSEMBLY_FILE_TYPE))


def _is_pyrevit_pkg_asm(asm_name, pkg):
    # if this is a pyRevit package assembly
    return (asm_name.startswith(SESSION_ID) and asm_name.endswith(pkg.unique_name))


def _is_pyrevit_already_loaded():
    logger.debug('Asking Revit for previously loaded pyrevit assemblies...')
    try:
        return _find_loaded_asm(_make_baseclasses_asm_name())
    except Exception as err:
        logger.debug('PyRevit is not loaded.')
        return False


def _is_pyrevit_pkg_already_loaded(pkg_asm_name):
    logger.debug('Asking Revit for previously loaded package assemblies: {}'.format(pkg_asm_name))
    return _find_loaded_asm(pkg_asm_name) is not None


def _is_any_pkg_asm_loaded(pkg):
    logger.debug('Asking Revit for any previously loaded package assemblies: {}'.format(pkg))
    for loaded_assembly in AppDomain.CurrentDomain.GetAssemblies():
        if _is_pyrevit_pkg_asm(loaded_assembly.GetName().Name, pkg):
            return True
    return False


def _is_pkg_asm_exists(pkg_asm_file_name):
    return op.exists(op.join(USER_TEMP_DIR, pkg_asm_file_name))


def _create_default_cmd_availability_type(modulebuilder, availability_class):
    type_builder = modulebuilder.DefineType(LOADER_ADDIN_COMMAND_DEFAULT_AVAIL_CLASS_NAME,
                                            TypeAttributes.Class | TypeAttributes.Public,
                                            availability_class)

    # call base constructor
    ci = availability_class.GetConstructor(Array[Type]([]))

    const_builder = type_builder.DefineConstructor(MethodAttributes.Public,
                                                   CallingConventions.Standard,
                                                   Array[Type](()))
    # add constructor parameters to stack
    gen = const_builder.GetILGenerator()
    gen.Emit(OpCodes.Ldarg_0)  # Load "this" onto eval stack
    gen.Emit(OpCodes.Call, ci)  # call base constructor (consumes "this" and the created stack)
    gen.Emit(OpCodes.Nop)  # Fill some space - this is how it is generated for equivalent C# code
    gen.Emit(OpCodes.Nop)
    gen.Emit(OpCodes.Nop)
    gen.Emit(OpCodes.Ret)
    type_builder.CreateType()


def _create_cmd_availability_type(modulebuilder, availability_class, loader_class_params):
    type_builder = modulebuilder.DefineType(loader_class_params.avail_class_name,
                                            TypeAttributes.Class | TypeAttributes.Public,
                                            availability_class)

    # call base constructor
    ci = availability_class.GetConstructor(Array[Type]([str]))

    const_builder = type_builder.DefineConstructor(MethodAttributes.Public,
                                                   CallingConventions.Standard,
                                                   Array[Type](()))
    # add constructor parameters to stack
    gen = const_builder.GetILGenerator()
    gen.Emit(OpCodes.Ldarg_0)  # Load "this" onto eval stack
    # Load the command context as a string onto stack
    gen.Emit(OpCodes.Ldstr, loader_class_params.cmd_context)
    gen.Emit(OpCodes.Call, ci)  # call base constructor (consumes "this" and the created stack)
    gen.Emit(OpCodes.Nop)  # Fill some space - this is how it is generated for equivalent C# code
    gen.Emit(OpCodes.Nop)
    gen.Emit(OpCodes.Nop)
    gen.Emit(OpCodes.Ret)
    type_builder.CreateType()


def _create_cmd_loader_type(modulebuilder, loader_class, loader_class_params):
    logger.debug('Creating loader class type for: {}'.format(loader_class_params))
    type_builder = modulebuilder.DefineType(loader_class_params.class_name,
                                            TypeAttributes.Class | TypeAttributes.Public,
                                            loader_class)

    # add RegenerationAttribute to type
    regen_const_info = clr.GetClrType(RegenerationAttribute).GetConstructor(Array[Type]((RegenerationOption,)))
    regen_attr_builder = CustomAttributeBuilder(regen_const_info,
                                                Array[object]((RegenerationOption.Manual,)))
    type_builder.SetCustomAttribute(regen_attr_builder)

    # add TransactionAttribute to type
    trans_constructor_info = clr.GetClrType(TransactionAttribute).GetConstructor(Array[Type]((TransactionMode,)))
    trans_attrib_builder = CustomAttributeBuilder(trans_constructor_info,
                                                  Array[object]((TransactionMode.Manual,)))
    type_builder.SetCustomAttribute(trans_attrib_builder)

    # call base constructor
    ci = loader_class.GetConstructor(Array[Type]((str, str, str, str, str, str)))

    const_builder = type_builder.DefineConstructor(MethodAttributes.Public,
                                                   CallingConventions.Standard,
                                                   Array[Type](()))
    # add constructor parameters to stack
    gen = const_builder.GetILGenerator()
    gen.Emit(OpCodes.Ldarg_0)  # Load "this" onto eval stack
    # Load the path to the command as a string onto stack
    gen.Emit(OpCodes.Ldstr, loader_class_params.script_file_address)
    # Load the config script path to the command as a string onto stack (for alternate click)
    gen.Emit(OpCodes.Ldstr, loader_class_params.config_script_file_address)
    # Load log file name into stack
    gen.Emit(OpCodes.Ldstr, SESSION_LOG_FILE_NAME)
    # Adding search paths to the stack (concatenated using ; as separator)
    gen.Emit(OpCodes.Ldstr, loader_class_params.search_paths_str)
    # set command name:
    gen.Emit(OpCodes.Ldstr, loader_class_params.cmd_name)
    # Adding command options to the stack (concatenated using ; as separator)
    gen.Emit(OpCodes.Ldstr, loader_class_params.cmd_options)
    gen.Emit(OpCodes.Call, ci)  # call base constructor (consumes "this" and the created stack)
    gen.Emit(OpCodes.Nop)  # Fill some space - this is how it is generated for equivalent C# code
    gen.Emit(OpCodes.Nop)
    gen.Emit(OpCodes.Nop)
    gen.Emit(OpCodes.Ret)
    type_builder.CreateType()


def _create_asm_file(pkg):
    # make unique assembly name for this package
    pkg_asm_name = _make_pkg_asm_name(pkg)
    # unique assembly filename for this package
    pkg_asm_file_name = pkg_asm_name + ASSEMBLY_FILE_TYPE

    # check to see if any older assemblies have been loaded for this package
    # this means that we currently have this package loaded and we're reloading a new version
    is_reloading_pkg = _is_any_pkg_asm_loaded(pkg)

    logger.debug('Building assembly for package: {}'.format(pkg))
    # compile_to_asm C# cstemplates code into a dll, then load and get the base class types from it
    loader_class = _find_pyrevit_base_class(LOADER_ADDIN_COMMAND_INTERFACE_CLASS_EXT)
    default_avail_class = _find_pyrevit_base_class(LOADER_ADDIN_COMMAND_DEFAULT_AVAIL_CLASS)
    category_avail_class = _find_pyrevit_base_class(LOADER_ADDIN_COMMAND_CAT_AVAIL_CLASS)
    selection_avail_class = _find_pyrevit_base_class(LOADER_ADDIN_COMMAND_SEL_AVAIL_CLASS)

    # create assembly
    windowsassemblyname = AssemblyName(Name=pkg_asm_name, Version=Version(PyRevitVersion.major,
                                                                          PyRevitVersion.minor,
                                                                          PyRevitVersion.patch, 0))
    logger.debug('Generated assembly name for this package: {0}'.format(pkg_asm_name))
    logger.debug('Generated windows assembly name for this package: {0}'.format(windowsassemblyname))
    logger.debug('Generated assembly file name for this package: {0}'.format(pkg_asm_file_name))
    assemblybuilder = AppDomain.CurrentDomain.DefineDynamicAssembly(windowsassemblyname,
                                                                    AssemblyBuilderAccess.RunAndSave, USER_TEMP_DIR)

    # get module builder
    modulebuilder = assemblybuilder.DefineDynamicModule(pkg_asm_name, pkg_asm_file_name)

    # create default availability class (this is for resetting buttons back to normal context state)
    _create_default_cmd_availability_type(modulebuilder, default_avail_class)

    # create command classes
    for loader_class_params in _get_params_for_commands(pkg):  # type: LoaderClassParams
        _create_cmd_loader_type(modulebuilder, loader_class, loader_class_params)
        if loader_class_params.cmd_context:
            if COMMAND_CONTEXT_SELECT_AVAIL == loader_class_params.cmd_context:
                _create_cmd_availability_type(modulebuilder, selection_avail_class, loader_class_params)
            else:
                _create_cmd_availability_type(modulebuilder, category_avail_class, loader_class_params)

    # save final assembly
    assemblybuilder.Save(pkg_asm_file_name)
    logger.debug('Executer assembly saved.')
    return PackageAssemblyInfo(pkg_asm_name, op.join(USER_TEMP_DIR, pkg_asm_file_name), is_reloading_pkg)


def _produce_asm_file(pkg):
    # make unique assembly name for this package
    pkg_asm_name = _make_pkg_asm_name(pkg)
    # unique assembly filename for this package
    pkg_asm_file_name = pkg_asm_name + ASSEMBLY_FILE_TYPE
    pkg_asm_file_path = op.join(USER_TEMP_DIR, pkg_asm_file_name)

    if _is_pyrevit_pkg_already_loaded(pkg_asm_name):
        logger.debug('Pakage assembly is already loaded: {}'.format(pkg_asm_name))
        return PackageAssemblyInfo(pkg_asm_name, pkg_asm_file_path, True)
    elif _is_pkg_asm_exists(pkg_asm_file_name):
        logger.debug('Pakage assembly file already exists: {}'.format(pkg_asm_file_path))
        _load_asm_file(pkg_asm_file_path)
        return PackageAssemblyInfo(pkg_asm_name, pkg_asm_file_path, False)
    else:
        return _create_asm_file(pkg)


def _cleanup_temp_asm_files():
    return True
    files = os.listdir(USER_TEMP_DIR)
    for file_name in files:
        if _is_pyrevit_asm_file(file_name):
            try:
                os.remove(op.join(USER_TEMP_DIR, file_name))
                logger.debug('Existing assembly file removed: {0}'.format(file_name))
            except OSError:
                # fixme: what if it can't delete the baseclasses file?
                logger.debug('Error deleting assembly file: {0}'.format(file_name))


def cleanup_existing_pyrevit_asm_files():
    running_rvt_instance_count = get_revit_instances()
    if running_rvt_instance_count > 1:
        logger.debug('Multiple Revit instance are running...Skipping assembly files cleanup')
    elif running_rvt_instance_count == 1 and _is_pyrevit_already_loaded():
        logger.debug('pyRevit is reloading. Skipping assembly file cleanup...')
    else:
        logger.debug('Cleaning up old pyrevit assembly files...')
        _cleanup_temp_asm_files()


def create_assembly(parsed_pkg):
    logger.debug('Initializing python script loader...')
    # create assembly file and return assembly file path to be used in UI creation
    try:
        pkg_asm_info = _produce_asm_file(parsed_pkg)
        logger.debug('Assembly created: {}'.format(pkg_asm_info))
        return pkg_asm_info
    except Exception as asm_err:
        logger.critical('Can not create assembly for: {} | {}'.format(parsed_pkg, asm_err))
