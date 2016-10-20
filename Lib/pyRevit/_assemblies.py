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
This is the module responsible for creating c# classes for commands and save them into a dll assembly.
The ui modules will later add the assembly and c# class information to the ui buttons.

All these four modules are private and handled by pyRevit.session
These modules do not import each other and mainly use base modules (.config, .logger, .exceptions, .output, .utils)
All these four modules can understand the component tree. (_basecomponents module)
 _parser parses the folders and creates a tree of components provided by _basecomponents
 _assemblies make a dll from the tree.
 _ui creates the ui using the information provided by the tree.
 _cache will save and restore the tree to increase loading performance.
"""

import os
import os.path as op
from collections import namedtuple

from .config import SESSION_ID, LOADER_ADDIN, LOADER_ADDIN_COMMAND_INTERFACE_CLASS_EXT, PYREVIT_ASSEMBLY_NAME
from .config import USER_TEMP_DIR, SESSION_STAMPED_ID, SESSION_DLL_NAME, SESSION_LOG_FILE_NAME, PyRevitVersion
from .config import SPECIAL_CHARS
from .exceptions import PyRevitLoaderNotFoundError
from .logger import logger
from .utils import join_paths

import clr
clr.AddReference('PresentationCore')
clr.AddReference('RevitAPI')
clr.AddReference('RevitAPIUI')
clr.AddReference('System.Xml.Linq')

# dot net imports
from System import AppDomain, Version, Array, Type
from System.IO import Path
from System.Reflection import AssemblyName, TypeAttributes, MethodAttributes, CallingConventions
from System.Reflection.Emit import AssemblyBuilderAccess, CustomAttributeBuilder, OpCodes
from System.Diagnostics import Process

# revit api imports
from Autodesk.Revit.Attributes import RegenerationAttribute, RegenerationOption, TransactionAttribute, TransactionMode


# Generic named tuple for passing loader class parameters to the assembly maker
LoaderClassParams = namedtuple('LoaderClassParams', ['class_name', 'script_file_address', 'search_paths_str'])


def _cleanup_class_name(name):
    for char, repl in SPECIAL_CHARS.items():
        name = name.replace(char, repl)
    return name


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
                return loader_class
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


def _get_params_for_commands(parsed_pkg):
    loader_params_for_all_cmds = []

    for cmd in parsed_pkg.get_all_commands():
        loader_params_for_all_cmds.append(LoaderClassParams(cmd.unique_name,
                                                            cmd.get_full_script_address(),
                                                            join_paths(cmd.get_search_paths())))

    return loader_params_for_all_cmds


def _create_dll_assembly(parsed_pkg, loader_class):
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

    # get module builder
    modulebuilder = assemblybuilder.DefineDynamicModule(SESSION_STAMPED_ID, SESSION_DLL_NAME)

    # create command classes
    for loader_class_params in _get_params_for_commands(parsed_pkg):
        type_builder = modulebuilder.DefineType(loader_class_params.class_name,
                                                TypeAttributes.Class | TypeAttributes.Public,
                                                loader_class)

        # add RegenerationAttribute to type
        regen_const_info = clr.GetClrType(RegenerationAttribute).GetConstructor(
            Array[Type]((RegenerationOption,)))
        regen_attr_builder = CustomAttributeBuilder(regen_const_info,
                                                    Array[object]((RegenerationOption.Manual,)))
        type_builder.SetCustomAttribute(regen_attr_builder)

        # add TransactionAttribute to type
        trans_constructor_info = clr.GetClrType(TransactionAttribute).GetConstructor(
            Array[Type]((TransactionMode,)))
        trans_attrib_builder = CustomAttributeBuilder(trans_constructor_info,
                                                      Array[object]((TransactionMode.Manual,)))
        type_builder.SetCustomAttribute(trans_attrib_builder)

        # call base constructor
        ci = loader_class.GetConstructor(Array[Type]((str, str, str,)))

        const_builder = type_builder.DefineConstructor(MethodAttributes.Public,
                                                       CallingConventions.Standard,
                                                       Array[Type](()))
        # add constructor parameters to stack
        gen = const_builder.GetILGenerator()
        gen.Emit(OpCodes.Ldarg_0)  # Load "this" onto eval stack
        # Load the path to the command as a string onto stack
        gen.Emit(OpCodes.Ldstr, loader_class_params.script_file_address)
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
    assemblybuilder.Save(SESSION_DLL_NAME)
    logger.debug('Executer assembly saved.')


def create_assembly(parsed_pkg):
    logger.debug('Initializing python script loader...')

    if not _is_pyrevit_already_loaded():
        _cleanup_existing_dlls()
    else:
        logger.debug('pyRevit is reloading. Skipping DLL and log cleanup.')

    # create dll and return assembly path to be used in UI creation
    _create_dll_assembly(parsed_pkg, _find_commandloader_class())
