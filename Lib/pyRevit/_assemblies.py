import os
import os.path as op
import shutil
from collections import namedtuple


from .config import SESSION_ID, LOADER_ADDIN, LOADER_ADDIN_COMMAND_INTERFACE_CLASS_EXT, PYREVIT_ASSEMBLY_NAME
from .config import USER_TEMP_DIR, SESSION_STAMPED_ID, SESSION_DLL_NAME, SESSION_LOG_FILE_NAME, PyRevitVersion
from .exceptions import PyRevitLoaderNotFoundError
from .logger import logger


# dot net imports
import clr
clr.AddReference('PresentationCore')
clr.AddReference('RevitAPI')
clr.AddReference('RevitAPIUI')
clr.AddReference('System.Xml.Linq')
from System import *
from System.IO import *
from System.Reflection import *
from System.Reflection.Emit import *
from System.Diagnostics import Process

# revit api imports
from Autodesk.Revit.Attributes import *


# Generic named tuple for returning assembly information.
PyRevitCommandLoaderAssemblyInfo = namedtuple('PyRevitCommandLoaderAssemblyInfo', ['assembly', 'cmd_loader_class'])


def _find_commandloader_class():
    """Private func: Finds the loader assembly addin and command interface class."""
    logger.debug('Asking Revit for command loader assembly...')
    for loaded_assembly in AppDomain.CurrentDomain.GetAssemblies():
        if LOADER_ADDIN in loaded_assembly.FullName:
            # Loader assembly is found
            # Getting the base command loader class
            logger.debug('Command loader assembly found: {0}'.format(loaded_assembly.GetName().FullName))
            loader_class = loaded_assembly.GetType(LOADER_ADDIN_COMMAND_INTERFACE_CLASS_EXT)
            if loader_class is not None:
                return PyRevitCommandLoaderAssemblyInfo(loaded_assembly, loader_class)
            else:
                logger.critical('Can not find command loader class type.')

    logger.critical('Can not find necessary command loader assembly.')
    raise PyRevitLoaderNotFoundError()


def _find_loaded_pyrevit_assemblies():
    """Private func: Collects information about previously loaded assemblies"""
    logger.debug('Asking Revit for previously loaded pyRevit assemblies...')
    loaded_py_revit_assemblies = []
    for loadedAssembly in AppDomain.CurrentDomain.GetAssemblies():
        if PYREVIT_ASSEMBLY_NAME in loadedAssembly.FullName:
            logger.debug('Existing assembly found: {0}'.format(loadedAssembly.FullName))
            # loadedPyRevitScripts.extend([ct.Name for ct in loadedAssembly.GetTypes()])
            loaded_py_revit_assemblies.append(loadedAssembly)

    return loaded_py_revit_assemblies


def _is_pyrevit_already_loaded():
    return len(_find_loaded_pyrevit_assemblies()) > 0


def _cleanup_existing_dlls():
    """Private func: Removes dlls from previous sessions from user temp directory."""
    revitinstances = list(Process.GetProcessesByName('Revit'))
    if len(revitinstances) > 1:
        logger.debug('Multiple Revit instance are running...Skipping DLL Cleanup')
    elif len(revitinstances) == 1:
        logger.debug('Cleaning up old DLL files...')
        files = os.listdir(USER_TEMP_DIR)
        for f in files:
            if f.startswith(SESSION_ID) and f.endswith('dll'):
                try:
                    os.remove(op.join(USER_TEMP_DIR, f))
                    logger.debug('Existing .Dll Removed: {0}'.format(f))
                except OSError:
                    logger.debug('Error deleting .DLL file: {0}'.format(f))


def _create_dll_assembly(command_list, loader_class):
    logger.debug('Building script executer assembly...')
    # make assembly dll name

    # create assembly
    windowsassemblyname = AssemblyName(Name=SESSION_STAMPED_ID, Version=Version(PyRevitVersion.major,
                                                                                PyRevitVersion.minor,
                                                                                PyRevitVersion.patch, 0))
    logger.debug('Generated assembly name for this session: {0}'.format(SESSION_STAMPED_ID))
    logger.debug('Generated windows assembly name for this session: {0}'.format(windowsassemblyname))
    logger.debug('Generated DLL name for this session: {0}'.format(SESSION_DLL_NAME))
    logger.debug('Generated log name for this session: {0}'.format(SESSION_LOG_FILE_NAME))
    assemblybuilder = AppDomain.CurrentDomain.DefineDynamicAssembly(windowsassemblyname,
                                                                    AssemblyBuilderAccess.RunAndSave, USER_TEMP_DIR)
    modulebuilder = assemblybuilder.DefineDynamicModule(SESSION_STAMPED_ID, SESSION_DLL_NAME)

    # create command classes
    # todo travere the tree instead of commands
    for cmd in command_list:
        # todo build the classname for cmd
        type_builder = modulebuilder.DefineType(cmd.className,
                                                TypeAttributes.Class | TypeAttributes.Public,
                                                loader_class)

        # add RegenerationAttribute to type
        regen_const_info = clr.GetClrType(RegenerationAttribute).GetConstructor(Array[Type]((RegenerationOption,)))
        regen_attr_builder = CustomAttributeBuilder(regen_const_info, Array[object]((RegenerationOption.Manual,)))
        type_builder.SetCustomAttribute(regen_attr_builder)

        # add TransactionAttribute to type
        trans_constructor_info = clr.GetClrType(TransactionAttribute).GetConstructor(Array[Type]((TransactionMode,)))
        trans_attrib_builder = CustomAttributeBuilder(trans_constructor_info, Array[object]((TransactionMode.Manual,)))
        type_builder.SetCustomAttribute(trans_attrib_builder)

        # call base constructor with script path
        ci = loader_class.GetConstructor(Array[Type]((str, str, str,)))

        const_builder = type_builder.DefineConstructor(MethodAttributes.Public,
                                                       CallingConventions.Standard,
                                                       Array[Type](()))
        gen = const_builder.GetILGenerator()
        gen.Emit(OpCodes.Ldarg_0)  # Load "this" onto eval stack
        # Load the path to the command as a string onto stack
        gen.Emit(OpCodes.Ldstr, cmd.get_full_script_address())
        # Load log file name into stack
        gen.Emit(OpCodes.Ldstr, SESSION_LOG_FILE_NAME)
        # Adding search paths to the stack. to simplify, concatenate using ; as separator
        # todo build search paths from tree component.directory params
        gen.Emit(OpCodes.Ldstr, ';'.join(cmd.search_path_list))
        gen.Emit(OpCodes.Call, ci)  # call base constructor (consumes "this" and the created stack)
        gen.Emit(OpCodes.Nop)       # Fill some space - this is how it is generated for equivalent C# code
        gen.Emit(OpCodes.Nop)
        gen.Emit(OpCodes.Nop)
        gen.Emit(OpCodes.Ret)
        type_builder.CreateType()

    # save final assembly
    assemblybuilder.Save(SESSION_DLL_NAME)
    logger.debug('Executer assembly saved.')
    return Path.Combine(USER_TEMP_DIR, SESSION_DLL_NAME)


def create_assembly(parsed_pkg):
    logger.debug('Initializing python script loader...')

    if not _is_pyrevit_already_loaded():
        _cleanup_existing_dlls()
    else:
        logger.debug('pyRevit is reloading. Skipping DLL and log cleanup.')

    # create dll and return assembly path to be used in UI creation
    return _create_dll_assembly(parsed_pkg.get_all_commands(), _find_commandloader_class().cmd_loader_class)
