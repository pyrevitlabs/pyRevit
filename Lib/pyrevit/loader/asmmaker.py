import clr
from collections import namedtuple

import pyrevit.coreutils.appdata as appdata
from pyrevit import PYREVIT_ADDON_NAME, HOST_VERSION
from pyrevit.coreutils import join_strings, load_asm_file, find_loaded_asm
from pyrevit.coreutils.logger import get_logger
from pyrevit.repo import PYREVIT_VERSION

from pyrevit.loader.cstemplates import get_cmd_class, get_cmd_avail_class, get_shared_classes

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

# Generic named tuple for passing assembly information to other modules
ExtensionAssemblyInfo = namedtuple('ExtensionAssemblyInfo', ['name', 'location', 'reloading'])


logger = get_logger(__name__)


ASSEMBLY_FILE_TYPE = 'dll'
# fixme: change script executor to write to this log file
SESSION_LOG_FILE = appdata.get_session_data_file('usagelog', 'log')
logger.info('Generated log name for this session: {}'.format(SESSION_LOG_FILE))


# Generic named tuple for passing loader class parameters to the assembly maker
class CommandExecutorParams:
    def __init__(self, script_cmp):
        self.cmd_name = script_cmp.name
        self.cmd_context = script_cmp.cmd_context
        self.cmd_options = join_strings(script_cmp.get_cmd_options())
        self.class_name = script_cmp.unique_name
        self.avail_class_name = script_cmp.unique_avail_name
        self.script_file_address = script_cmp.get_full_script_address()
        self.config_script_file_address = script_cmp.get_full_config_script_address()
        self.search_paths_str = join_strings(script_cmp.get_search_paths())


def _make_ext_asm_name(extension):
    return '{}{}_{}_{}'.format(PYREVIT_ADDON_NAME, HOST_VERSION, extension.hash_value, extension.unique_name)


def _make_ext_asm_fileid(extension):
    return '{}_{}'.format(extension.hash_value, extension.unique_name)


def _is_pyrevit_ext_asm(asm_name, extension):
    # if this is a pyRevit package assembly
    return asm_name.startswith(PYREVIT_ADDON_NAME) and asm_name.endswith(extension.unique_name)


def _is_pyrevit_ext_already_loaded(pkg_asm_name):
    logger.debug('Asking Revit for previously loaded package assemblies: {}'.format(pkg_asm_name))
    return find_loaded_asm(pkg_asm_name) is not None


def _is_any_ext_asm_loaded(extension):
    logger.debug('Asking Revit for any previously loaded package assemblies: {}'.format(extension))
    for loaded_assembly in AppDomain.CurrentDomain.GetAssemblies():
        if _is_pyrevit_ext_asm(loaded_assembly.GetName().Name, extension):
            return True
    return False


def _get_params_for_commands(parent_cmp):
    logger.debug('Creating a list of commands for the assembly maker from: {}'.format(parent_cmp))
    loader_params_for_all_cmds = []

    for sub_cmp in parent_cmp:
        if sub_cmp.is_container():
            loader_params_for_all_cmds.extend(_get_params_for_commands(sub_cmp))
        else:
            try:
                logger.debug('Command found: {}'.format(sub_cmp))
                loader_params_for_all_cmds.append(CommandExecutorParams(sub_cmp))
            except Exception as err:
                logger.debug('Can not create class parameters from: {} | {}'.format(sub_cmp, err))

    return loader_params_for_all_cmds


def _create_basic_type(modulebuilder, type_class, class_name):
    # create type builder
    type_builder = modulebuilder.DefineType(class_name, TypeAttributes.Class | TypeAttributes.Public, type_class)
    # call base constructor
    ci = type_class.GetConstructor(Array[Type]([]))
    # create class constructor builder
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


def _create_cmd_loader_type(modulebuilder, loader_class, cmd_params):
    logger.debug('Creating loader class type for: {}'.format(cmd_params))
    type_builder = modulebuilder.DefineType(cmd_params.class_name,
                                            TypeAttributes.Class | TypeAttributes.Public,
                                            loader_class)

    # add RegenerationAttribute to type
    regen_const_info = clr.GetClrType(RegenerationAttribute).GetConstructor(Array[Type]((RegenerationOption,)))
    regen_attr_builder = CustomAttributeBuilder(regen_const_info,
                                                Array[object]((RegenerationOption.Manual,))
                                                )
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
    gen.Emit(OpCodes.Ldstr, cmd_params.script_file_address)
    # Load the config script path to the command as a string onto stack (for alternate click)
    gen.Emit(OpCodes.Ldstr, cmd_params.config_script_file_address)
    # Load log file name into stack
    gen.Emit(OpCodes.Ldstr, SESSION_LOG_FILE)
    # Adding search paths to the stack (concatenated using ; as separator)
    gen.Emit(OpCodes.Ldstr, cmd_params.search_paths_str)
    # set command name:
    gen.Emit(OpCodes.Ldstr, cmd_params.cmd_name)
    # Adding command options to the stack (concatenated using ; as separator)
    gen.Emit(OpCodes.Ldstr, cmd_params.cmd_options)
    gen.Emit(OpCodes.Call, ci)  # call base constructor (consumes "this" and the created stack)
    gen.Emit(OpCodes.Nop)  # Fill some space - this is how it is generated for equivalent C# code
    gen.Emit(OpCodes.Nop)
    gen.Emit(OpCodes.Nop)
    gen.Emit(OpCodes.Ret)
    type_builder.CreateType()


def _create_asm_file(extension):
    # make unique assembly name for this package
    ext_asm_name = _make_ext_asm_name(extension)
    # unique assembly filename for this package
    ext_asm_fileid = _make_ext_asm_fileid(extension)
    ext_asm_file_name = appdata.get_data_file(file_id=ext_asm_fileid,
                                              file_ext=ASSEMBLY_FILE_TYPE, name_only=True)
    ext_asm_file_path = appdata.get_data_file(file_id=ext_asm_fileid,
                                              file_ext=ASSEMBLY_FILE_TYPE)

    # check to see if any older assemblies have been loaded for this package
    # this means that we currently have this package loaded and we're reloading a new version
    is_reloading_pkg = _is_any_ext_asm_loaded(extension)

    # create assembly
    logger.debug('Building assembly for package: {}'.format(extension))
    windowsassemblyname = AssemblyName(Name=ext_asm_name, Version=Version(PYREVIT_VERSION.major,
                                                                          PYREVIT_VERSION.minor,
                                                                          PYREVIT_VERSION.patch, 0))
    logger.debug('Generated assembly name for this package: {0}'.format(ext_asm_name))
    logger.debug('Generated windows assembly name for this package: {0}'.format(windowsassemblyname))
    logger.debug('Generated assembly file name for this package: {0}'.format(ext_asm_file_name))
    assemblybuilder = AppDomain.CurrentDomain.DefineDynamicAssembly(windowsassemblyname,
                                                                    AssemblyBuilderAccess.RunAndSave,
                                                                    appdata.PYREVIT_APP_DIR)

    # get module builder
    modulebuilder = assemblybuilder.DefineDynamicModule(ext_asm_name, ext_asm_file_name)

    # create classes that could be called from any button (shared classes)
    # currently only default availability class is implemented. default availability class is for resetting
    # buttons back to normal context state (when reloading and after their context has changed during a session).
    for shared_class, class_name in get_shared_classes():
        _create_basic_type(modulebuilder, shared_class, class_name)

    # create command classes
    for cmd_params in _get_params_for_commands(extension):  # type: CommandExecutorParams
        # create command executor class for this command
        # fixme: create command_type param and change cmd_params.cmd_name here
        _create_cmd_loader_type(modulebuilder, get_cmd_class(cmd_params.cmd_name), cmd_params)

        # create command availability class for this command
        cmd_avail_class, cmd_avail_class_name = get_cmd_avail_class(cmd_params.avail_class_name)
        _create_basic_type(modulebuilder, cmd_avail_class, cmd_avail_class_name)

    # save final assembly
    assemblybuilder.Save(ext_asm_file_name)
    logger.debug('Executer assembly saved.')
    return ExtensionAssemblyInfo(ext_asm_name, ext_asm_file_path, is_reloading_pkg)


def _produce_asm_file(extension):
    # make unique assembly name for this package
    ext_asm_name = _make_ext_asm_name(extension)
    # unique assembly filename for this package
    ext_asm_fileid = _make_ext_asm_fileid(extension)
    ext_asm_file_path = appdata.get_data_file(file_id=ext_asm_fileid,
                                              file_ext=ASSEMBLY_FILE_TYPE)

    if _is_pyrevit_ext_already_loaded(ext_asm_name):
        logger.debug('Extension assembly is already loaded: {}'.format(ext_asm_name))
        return ExtensionAssemblyInfo(ext_asm_name, ext_asm_file_path, True)
    elif appdata.is_data_file_available(file_id=ext_asm_fileid, file_ext=ASSEMBLY_FILE_TYPE):
        logger.debug('Extension assembly file already exists: {}'.format(ext_asm_file_path))
        load_asm_file(ext_asm_file_path)
        return ExtensionAssemblyInfo(ext_asm_name, ext_asm_file_path, False)
    else:
        return _create_asm_file(extension)


def create_assembly(parsed_ext):
    logger.debug('Initializing python script loader...')
    # create assembly file and return assembly file path to be used in UI creation
    try:
        ext_asm_info = _produce_asm_file(parsed_ext)
        logger.debug('Assembly created: {}'.format(ext_asm_info))
        return ext_asm_info
    except Exception as asm_err:
        logger.critical('Can not create assembly for: {} | {}'.format(parsed_ext, asm_err))
