import os
import os.path as op
import shutil
from datetime import datetime

from .config import SESSION_ID, LOADER_ADDIN, LOADER_ADDIN_COMMAND_INTERFACE_CLASS_EXT, PYREVIT_ASSEMBLY_NAME
from .config import USER_TEMP_DIR, PyRevitVersion
from .exceptions import *
from .logger import logger

from .usersettings import user_settings

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


class PyRevitCommandsAssembly():
    """Wrapper for all interactions with existing and new pyRevit assemblies and associated dll files."""
    def __init__(self, commands):
        self._session_label = "{}_{}".format(cfg.SESSION_ID, datetime.now().strftime('%y%m%d%H%M%S'))
        self._log_filename = self._session_label + '.log'
        self._loadedPyRevitAssemblies = []

        self.name = self._session_label
        self.loader_available = False
        self.extended_loader_available = False
        self.commandLoaderClass = None
        self.commandLoaderAssembly = None

        self.command_list = commands

        logger.debug('Initializing python script loader...')

        if not self._find_commandloader_class():
            logger.critical('pyRevit load failed...Can not find necessary command loader class.')
            raise PyRevitLoaderNotFoundError()

        self._find_loaded_pyrevit_assemblies()

        if not self.is_pyrevit_already_loaded():
            self._cleanup_existing_dlls()
            self._archivelogs()
        else:
            logger.debug('pyRevit is reloading. Skipping DLL and log cleanup.')

        self.dll_location = self._create_dll_assembly()

    def _find_commandloader_class(self):
        """PRIVATE: Finds the loader assembly adding and command interface class."""
        logger.debug('Asking Revit for command loader assembly...')
        for loadedAssembly in AppDomain.CurrentDomain.GetAssemblies():
            if cfg.LOADER_ADDIN in loadedAssembly.FullName:
                # Loader assembly is found
                logger.debug('Command loader assembly found: {0}'.format(loadedAssembly.GetName().FullName))
                self.commandLoaderAssembly = loadedAssembly

                # Getting the base command loader class
                loader_class = loadedAssembly.GetType(cfg.LOADER_ADDIN_COMMAND_INTERFACE_CLASS_EXT)
                if loader_class is not None:
                    self.commandLoaderClass = loader_class
                    self.loader_available = True
                else:
                    return None

                return True

        logger.error('Can not find command loader assembly.')
        return None

    def _find_loaded_pyrevit_assemblies(self):
        """PRIVATE: Collect information about previously loaded assemblies"""
        logger.debug('Asking Revit for previously loaded pyRevit assemblies...')
        for loadedAssembly in AppDomain.CurrentDomain.GetAssemblies():
            if cfg.PYREVIT_ASSEMBLY_NAME in loadedAssembly.FullName:
                logger.debug('Existing assembly found: {0}'.format(loadedAssembly.FullName))
                # self.loadedPyRevitScripts.extend([ct.Name for ct in loadedAssembly.GetTypes()])
                self._loadedPyRevitAssemblies.append(loadedAssembly)

    def _cleanup_existing_dlls(self):
        revitinstances = list(Process.GetProcessesByName('Revit'))
        if len(revitinstances) > 1:
            logger.debug('Multiple Revit instance are running...Skipping DLL Cleanup')
        elif len(revitinstances) == 1:
            logger.debug('Cleaning up old DLL files...')
            files = os.listdir(cfg.USER_TEMP_DIR)
            for f in files:
                if f.startswith(cfg.SESSION_ID) and f.endswith('dll'):
                    try:
                        os.remove(op.join(cfg.USER_TEMP_DIR, f))
                        logger.debug('Existing .Dll Removed: {0}'.format(f))
                    except:
                        logger.debug('Error deleting .DLL file: {0}'.format(f))

    def _archivelogs(self):
        if op.exists(user_settings.archivelogfolder):
            revitinstances = list(Process.GetProcessesByName('Revit'))
            if len(revitinstances) > 1:
                logger.debug('Multiple Revit instance are running...Skipping archiving old log files.')
            elif len(revitinstances) == 1:
                logger.debug('Archiving old log files...')
                files = os.listdir(cfg.USER_TEMP_DIR)
                for f in files:
                    if f.startswith(cfg.PYREVIT_ASSEMBLY_NAME) and f.endswith('log'):
                        try:
                            currentfileloc = op.join(cfg.USER_TEMP_DIR, f)
                            newloc = op.join(user_settings.archivelogfolder, f)
                            shutil.move(currentfileloc, newloc)
                            logger.debug('Existing log file archived to: {0}'.format(newloc))
                        except:
                            logger.debug('Error archiving log file: {0}'.format(f))
        else:
            logger.debug('Archive log folder does not exist: {0}. Skipping...'.format(user_settings.archivelogfolder))

    def is_pyrevit_already_loaded(self):
        """Returns true if any pyrevit module is loaded in current Revit session."""
        return len(self._loadedPyRevitAssemblies) > 0

    def _create_dll_assembly(self):
        logger.debug('Building script executer assembly...')
        # make assembly dll name
        dllname = self._session_label + '.dll'

        # create assembly
        windowsassemblyname = AssemblyName(Name=self._session_label, Version=Version(cfg.PyRevitVersion.major,
                                                                                     cfg.PyRevitVersion.minor,
                                                                                     cfg.PyRevitVersion.patch, 0))
        logger.debug('Generated assembly name for this session: {0}'.format(self._session_label))
        logger.debug('Generated windows assembly name for this session: {0}'.format(windowsassemblyname))
        logger.debug('Generated DLL name for this session: {0}'.format(dllname))
        logger.debug('Generated log name for this session: {0}'.format(self._log_filename))
        assemblybuilder = AppDomain.CurrentDomain.DefineDynamicAssembly(windowsassemblyname,
                                                                        AssemblyBuilderAccess.RunAndSave, cfg.USER_TEMP_DIR)
        modulebuilder = assemblybuilder.DefineDynamicModule(self._session_label, dllname)

        # create command classes
        for cmd in self.command_list:
            type_builder = modulebuilder.DefineType(cmd.className,
                                                   TypeAttributes.Class | TypeAttributes.Public,
                                                   self.commandLoaderClass)

            # add RegenerationAttribute to type
            regen_const_info = clr.GetClrType(RegenerationAttribute).GetConstructor(
                Array[Type]((RegenerationOption,)))
            regen_attr_builder = CustomAttributeBuilder(regen_const_info,
                                                                Array[object]((RegenerationOption.Manual,)))
            type_builder.SetCustomAttribute(regen_attr_builder)

            # add TransactionAttribute to type
            transactionconstructorinfo = clr.GetClrType(TransactionAttribute).GetConstructor(
                Array[Type]((TransactionMode,)))
            transactionattributebuilder = CustomAttributeBuilder(transactionconstructorinfo,
                                                                 Array[object]((TransactionMode.Manual,)))
            type_builder.SetCustomAttribute(transactionattributebuilder)

            # call base constructor with script path
            ci = None
            if self.loader_available:
                ci = self.commandLoaderClass.GetConstructor(Array[Type]((str, str, str,)))
            else:
                raise PyRevitLoaderNotFoundError()

            const_builder = type_builder.DefineConstructor(MethodAttributes.Public,
                                                           CallingConventions.Standard,
                                                           Array[Type](()))
            gen = const_builder.GetILGenerator()
            gen.Emit(OpCodes.Ldarg_0)  # Load "this" onto eval stack
            # Load the path to the command as a string onto stack
            gen.Emit(OpCodes.Ldstr, cmd.getfullscriptaddress())
            # Load log file name into stack
            gen.Emit(OpCodes.Ldstr, self._log_filename)
            # Adding search paths to the stack
            gen.Emit(OpCodes.Ldstr, cmd.search_paths)
            gen.Emit(OpCodes.Call, ci)  # call base constructor (consumes "this" and the created stack)
            gen.Emit(OpCodes.Nop)  # Fill some space - this is how it is generated for equivalent C# code
            gen.Emit(OpCodes.Nop)
            gen.Emit(OpCodes.Nop)
            gen.Emit(OpCodes.Ret)
            type_builder.CreateType()

        # save final assembly
        assemblybuilder.Save(dllname)
        logger.debug('Executer assembly saved.')
        return Path.Combine(cfg.USER_TEMP_DIR, dllname)
