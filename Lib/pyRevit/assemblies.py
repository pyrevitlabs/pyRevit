"""
assemblies.py
This module has 2 responsibilities:
1. Find the revitpythonloader.dll that has been loaded into revit
by the addin file, and return the commandLoaderBase class
so it can be used as a base class for all python scripts.
2. Create a temporary Dynamic Assembly (DLL) with a class
representing each pyrevit script, and a path to the python script,
so that Script Executor can pull the source code and run it through
the Iron Python Shell
https://github.com/architecture-building-systems/revitpythonshell/blob/e44f46a1e0b06675e7f1d9bc4870a021e79af0c3/RpsRuntime/ExternalCommandAssemblyBuilder.cs

"""

import os
import clr
import time
from datetime import datetime

from System import Array, Type
from System import AppDomain, Version
from System.Reflection import AssemblyName, TypeAttributes
from System.Reflection import CallingConventions, MethodAttributes
from System.Reflection.Emit import AssemblyBuilderAccess
from System.Reflection.Emit import CustomAttributeBuilder, OpCodes
# from System.IO import *

from Autodesk.Revit.Attributes import RegenerationOption, RegenerationAttribute
from Autodesk.Revit.Attributes import TransactionAttribute, TransactionMode
from Autodesk.Revit.Exceptions import ApplicationException, ArgumentException

from loader.logger import logger
from loader.exceptions import PyRevitException
from loader.config import ASSEMBLY_NAME, CMD_LOADER_BASE
from loader.config import SCRIPTS_DLL_BASENAME, TEMPDIR


def get_cmd_loader_base():
    """Finds the DLL Python Loader Assembly, which was added by the .addin
    This Assembly is only used to extract the CommandLoaderBase Class which
    will be used as reference by the scripts"""
    for loaded_assembly in AppDomain.CurrentDomain.GetAssemblies():
        if ASSEMBLY_NAME in loaded_assembly.FullName:
            logger.debug('Loader Assembly Found: : {0}'.format(
                                            loaded_assembly.GetName().FullName))
            cmd_loader_base = loaded_assembly.GetType(CMD_LOADER_BASE)
            break
    else:
        raise PyRevitException('Could not find Assembly')
    return cmd_loader_base

def make_scripts_dll(command_loader, commands):
    """Creates a dynamic library to reference python scripts.
    This assembly will include one class for each script, with the
    fullpath to the script as the scriptsource variable.
    The classes are created dynamically.

    :command_loader: class type from assembly scripts will inherit from
    :commands: list of command tuples that will be added to scripts assmbly
    command.class_name = name of command class
    command.py_filepath = full path to python script

    returns scripts_assmebly_path
    """
    logger.title('Making Scripts DLL.')


    dll_timestamp = str(time.time())                          # Unique Per Reload
    scripts_dll_name = "{0}_{1}".format(SCRIPTS_DLL_BASENAME, dll_timestamp)
    scripts_dll_filename = scripts_dll_name + '.dll'
    scripts_dll_filepath = os.path.join(TEMPDIR, scripts_dll_filename)

    # create assembly
    windowsassemblyname = AssemblyName(Name=scripts_dll_name,
                                       Version=Version(1, 0, 0, 0))

    assemblybuilder = AppDomain.CurrentDomain.DefineDynamicAssembly(windowsassemblyname, AssemblyBuilderAccess.RunAndSave,
                                                                    TEMPDIR)
    modulebuilder = assemblybuilder.DefineDynamicModule(scripts_dll_name,
                                                        scripts_dll_filename)

    for command in commands:
        # create command classes
        # logger.debug('[{}] Adding to DLL'.format(command.class_name))

        try:
            typebuilder = modulebuilder.DefineType(command.class_name,
                                   TypeAttributes.Class | TypeAttributes.Public,
                                   command_loader)

        except Exception as errmsg:
            logger.error('Error:: {}'.format(command.class_name))
            logger.error(errmsg)
            continue

        # add RegenerationAttribute to type
        regenerationconstrutorinfo = clr.GetClrType(RegenerationAttribute).GetConstructor(Array[Type]((RegenerationOption,)))
        regenerationattributebuilder = CustomAttributeBuilder(regenerationconstrutorinfo, Array[object]((RegenerationOption.Manual,)))
        typebuilder.SetCustomAttribute(regenerationattributebuilder)

        # add TransactionAttribute to type
        transactionconstructorinfo = clr.GetClrType(TransactionAttribute).GetConstructor(Array[Type]((TransactionMode,)))
        transactionattributebuilder = CustomAttributeBuilder(transactionconstructorinfo,Array[object]((TransactionMode.Manual,)))
        typebuilder.SetCustomAttribute(transactionattributebuilder)
        #
        # # call base constructor with script path
        constructorbuilder = typebuilder.DefineConstructor(MethodAttributes.Public, CallingConventions.Standard, Array[Type](()))
        gen = constructorbuilder.GetILGenerator()
        # Load "this" onto eval stack
        gen.Emit(OpCodes.Ldarg_0)
        # Load the path to the command as a string onto stack
        gen.Emit(OpCodes.Ldstr, command.py_filepath)
        # call base constructor (consumes "this" and the string)
        ci = command_loader.GetConstructor(Array[Type]((str,)))
        gen.Emit(OpCodes.Call, ci)
        # Fill some space - this is how it is generated for equivalent C# code
        gen.Emit(OpCodes.Nop)
        gen.Emit(OpCodes.Nop)
        gen.Emit(OpCodes.Nop)
        gen.Emit(OpCodes.Ret)
        typebuilder.CreateType()
        logger.debug('[{}] class added to DLL'.format(command.class_name))
        #
    if commands:
        assemblybuilder.Save(scripts_dll_filename)
        logger.debug('DLL Created.')
    else:
        logger.warning('No Commands to create DLL.')
    return scripts_dll_filepath, scripts_dll_filename
