""" Module name = _assemblies.py
Copyright (c) 2014-2016 Ehsan Iran-Nejad
Python scripts for Autodesk Revit

This file is part of pyRevit repository at https://github.com/eirannejad/pyRevit

pyRevit is a free set of scripts for Autodesk Revit: you can redistribute it and/or modify
it under the terms of the GNU General Public License version 3, as published by
the Free Software Foundation.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

See this link for a copy of the GNU General Public License protecting this package.
https://github.com/eirannejad/pyRevit/blob/master/LICENSE


~~~
Description:
pyRevit library has 4 main modules for handling parsing, assembly creation, ui, and caching.
This is the module responsible for creating c# classes for commands and save them into an assembly file.
The ui modules will later add the assembly and c# class information to the ui buttons.

All these four modules are private and handled by pyRevit.session
These modules do not import each other and mainly use base modules (.config, .logger, .exceptions, .output, .utils)
All these four modules can understand the component tree. (_basecomponents module)
 _parser parses the folders and creates a tree of components provided by _basecomponents
 _assemblies make an assembly from the tree.
 _ui creates the ui using the information provided by the tree.
 _cache will save and restore the tree to increase loading performance.
"""

import os
import os.path as op
from collections import namedtuple

from ..config import SESSION_ID, LOADER_ADDIN, LOADER_ADDIN_COMMAND_INTERFACE_CLASS_EXT
from ..config import USER_TEMP_DIR, SESSION_STAMPED_ID, ASSEMBLY_FILE_TYPE, SESSION_LOG_FILE_NAME
from ..config import REVISION_EXTENSION
from ..config import SPECIAL_CHARS, PyRevitVersion
from ..exceptions import PyRevitLoaderNotFoundError
from ..logger import logger
from ..utils import join_paths, get_revit_instances

# dot net imports
import clr
clr.AddReference('PresentationCore')
clr.AddReference('RevitAPI')
clr.AddReference('RevitAPIUI')
clr.AddReference('System.Xml.Linq')
from System import AppDomain, Version, Array, Type
from System.Reflection import AssemblyName, TypeAttributes, MethodAttributes, CallingConventions
from System.Reflection.Emit import AssemblyBuilderAccess, CustomAttributeBuilder, OpCodes

# revit api imports
from Autodesk.Revit.Attributes import RegenerationAttribute, RegenerationOption, TransactionAttribute, TransactionMode


# Generic named tuple for passing assembly information to other modules
PackageAssemblyInfo = namedtuple('PackageAssemblyInfo', ['name', 'location', 'reloading'])

# Generic named tuple for passing loader class parameters to the assembly maker
LoaderClassParams = namedtuple('LoaderClassParams',
                               ['class_name', 'script_file_address', 'config_script_file_address', 'search_paths_str'])


def _make_pkg_asm_name(pkg):
    return SESSION_STAMPED_ID + '_' + pkg.unique_name


def _make_pkg_asm_name_revised(pkg):
    pkg_dll_name = _make_pkg_asm_name(pkg)
    # if package is already loaded, add revision extension to pkg_dll_name (_R1, _R2,...)
    if _is_package_already_loaded(pkg):
        rev_num = 1
        while True:
            reload_pkg_dll_name = pkg_dll_name + REVISION_EXTENSION.format(rev_num)
            logger.debug('Trying new dll file name: {}'.format(reload_pkg_dll_name))
            if not op.exists(op.join(USER_TEMP_DIR, reload_pkg_dll_name + ASSEMBLY_FILE_TYPE)):
                logger.debug('New dll name created: {}'.format(reload_pkg_dll_name))
                pkg_dll_name = reload_pkg_dll_name
                break
            else:
                rev_num += 1

    return pkg_dll_name


def _is_pkg_asm_file(pkg, file_name):
    # if this is a pyRevit assembly file
    if file_name.startswith(SESSION_ID) and file_name.endswith(ASSEMBLY_FILE_TYPE):
        # return true if it belongs to this package
        return pkg.unique_name in file_name
    return False


def _find_commandloader_class():
    """Private func: Finds the loader assembly addin and command interface class."""
    logger.debug('Asking Revit for command loader assembly...')
    for loaded_assembly in AppDomain.CurrentDomain.GetAssemblies():
        if LOADER_ADDIN.lower() in str(loaded_assembly.FullName).lower():
            # Loader assembly is found
            # Getting the base command loader class
            logger.debug('Command loader assembly found: {0}'.format(loaded_assembly.GetName().FullName))
            loader_class = loaded_assembly.GetType(LOADER_ADDIN_COMMAND_INTERFACE_CLASS_EXT)
            if loader_class is not None:
                return loader_class
            else:
                logger.critical('Can not find command loader class type.')

    logger.critical('Can not find necessary command loader assembly.')
    raise PyRevitLoaderNotFoundError()


def _find_loaded_package_assemblies(pkg):
    """Private func: Collects information about previously loaded assemblies"""
    logger.debug('Asking Revit for previously loaded package assemblies...: {}'.format(pkg))
    loaded_pkg_assemblies = []
    pkg_assembly_name = _make_pkg_asm_name(pkg)
    for loadedAssembly in AppDomain.CurrentDomain.GetAssemblies():
        if pkg_assembly_name in loadedAssembly.FullName:
            logger.debug('Existing assembly found: {0}'.format(loadedAssembly.FullName))
            # loadedPyRevitScripts.extend([ct.Name for ct in loadedAssembly.GetTypes()])
            loaded_pkg_assemblies.append(loadedAssembly)

    return loaded_pkg_assemblies


def _is_package_already_loaded(pkg):
    return len(_find_loaded_package_assemblies(pkg)) > 0


def _cleanup_existing_package_asm_files(pkg):
    """Private func: Removes assembly files from previous sessions from user temp directory."""
    logger.debug('Cleaning up old package assembly files...: {}'.format(pkg))
    files = os.listdir(USER_TEMP_DIR)
    for file_name in files:
        if _is_pkg_asm_file(pkg, file_name):
            try:
                os.remove(op.join(USER_TEMP_DIR, file_name))
                logger.debug('Existing assembly file removed: {0}'.format(file_name))
            except OSError:
                logger.debug('Error deleting assembly file: {0}'.format(file_name))


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
                                                                    sub_cmp.get_full_script_address(),
                                                                    sub_cmp.get_full_config_script_address(),
                                                                    join_paths(sub_cmp.get_search_paths())))
            except Exception as err:
                logger.debug('Can not create class parameters from: {} | {}'.format(sub_cmp, err))

    return loader_params_for_all_cmds


def _create_asm_file(pkg, loader_class, pkg_reloading):
    logger.debug('Building script executer assembly...')

    # make unique assembly name for this package
    pkg_asm_name = _make_pkg_asm_name_revised(pkg) if pkg_reloading else _make_pkg_asm_name(pkg)
    # unique assembly filename for this package
    pkg_asm_file_name = pkg_asm_name + ASSEMBLY_FILE_TYPE

    # create assembly
    windowsassemblyname = AssemblyName(Name=pkg_asm_name, Version=Version(PyRevitVersion.major,
                                                                          PyRevitVersion.minor,
                                                                          PyRevitVersion.patch, 0))
    logger.debug('Generated assembly name for this package: {0}'.format(pkg_asm_name))
    logger.debug('Generated windows assembly name for this package: {0}'.format(windowsassemblyname))
    logger.info('Generated assembly file name for this package: {0}'.format(pkg_asm_file_name))
    assemblybuilder = AppDomain.CurrentDomain.DefineDynamicAssembly(windowsassemblyname,
                                                                    AssemblyBuilderAccess.RunAndSave, USER_TEMP_DIR)

    # get module builder
    modulebuilder = assemblybuilder.DefineDynamicModule(pkg_asm_name, pkg_asm_file_name)

    # create command classes
    for loader_class_params in _get_params_for_commands(pkg):
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
        ci = loader_class.GetConstructor(Array[Type]((str, str, str, str)))

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
        # Adding search paths to the stack. to simplify, concatenate using ; as separator
        gen.Emit(OpCodes.Ldstr, loader_class_params.search_paths_str)
        gen.Emit(OpCodes.Call, ci)  # call base constructor (consumes "this" and the created stack)
        gen.Emit(OpCodes.Nop)  # Fill some space - this is how it is generated for equivalent C# code
        gen.Emit(OpCodes.Nop)
        gen.Emit(OpCodes.Nop)
        gen.Emit(OpCodes.Ret)
        type_builder.CreateType()

    # save final assembly
    assemblybuilder.Save(pkg_asm_file_name)
    logger.debug('Executer assembly saved.')
    return PackageAssemblyInfo(pkg_asm_name, op.join(USER_TEMP_DIR, pkg_asm_file_name), pkg_reloading)


def create_assembly(parsed_pkg):
    logger.debug('Initializing python script loader...')

    pkg_reloading = _is_package_already_loaded(parsed_pkg)

    running_rvt_instance_count = get_revit_instances()
    if running_rvt_instance_count > 1:
        logger.debug('Multiple Revit instance are running...Skipping assembly files cleanup')
    elif running_rvt_instance_count == 1 and pkg_reloading:
        logger.debug('pyRevit is reloading. Skipping assembly file cleanup...')
    else:
        _cleanup_existing_package_asm_files(parsed_pkg)

    # create assembly file and return assembly file path to be used in UI creation
    pkg_asm_info = _create_asm_file(parsed_pkg, _find_commandloader_class(), pkg_reloading)
    logger.debug('Assembly created: {}'.format(pkg_asm_info))
    return pkg_asm_info
