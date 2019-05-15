"""
The loader module manages the workflow of loading a new pyRevit session.
It's main purpose is to orchestrate the process of finding pyRevit extensions,
creating dll assemblies for them, and creating a user interface
in the host application.

Everything starts from ``sessionmgr.load_session()`` function...

The only public function is ``load_session()`` that loads a new session.
Everything else is private.
"""

import os.path as op
import sys
from collections import namedtuple

from pyrevit import EXEC_PARAMS, HOST_APP
from pyrevit import coreutils
from pyrevit.framework import FormatterServices
from pyrevit.framework import Array
from pyrevit.coreutils import Timer
from pyrevit.coreutils import envvars
from pyrevit.coreutils import appdata
from pyrevit.coreutils import logger
from pyrevit.loader import sessioninfo
from pyrevit.loader import asmmaker
from pyrevit.loader import uimaker
from pyrevit.userconfig import user_config
from pyrevit.extensions import COMMAND_AVAILABILITY_NAME_POSTFIX
from pyrevit.extensions import extensionmgr
from pyrevit import usagelog
from pyrevit.versionmgr import updater
from pyrevit.versionmgr import upgrade
# import the basetypes first to get all the c-sharp code to compile
from pyrevit.loader.basetypes import LOADER_BASE_NAMESPACE
from pyrevit.coreutils import loadertypes
# now load the rest of module that could depend on the compiled basetypes
from pyrevit import output

from pyrevit import DB, UI, revit


#pylint: disable=W0703,C0302,C0103
mlogger = logger.get_logger(__name__)


AssembledExtension = namedtuple('AssembledExtension', ['ext', 'assm'])


def _clear_running_engines():
    # clear the cached engines
    try:
        my_output = output.get_output()
        if my_output:
            my_output.close_others(all_open_outputs=True)

        EXEC_PARAMS.engine_mgr.ClearEngines()
    except AttributeError:
        return False


def _setup_output():
    # create output window and assign handle
    out_window = loadertypes.ScriptOutput()
    runtime_info = sessioninfo.get_runtime_info()
    out_window.AppVersion = '{}:{}:{}'.format(
        runtime_info.pyrevit_version,
        runtime_info.engine_version,
        runtime_info.host_version
        )

    # create output stream and set stdout to it
    # we're not opening the output window here.
    # The output stream will open the window if anything is being printed.
    outstr = loadertypes.ScriptOutputStream(out_window)
    sys.stdout = outstr
    # sys.stderr = outstr
    stdout_hndlr = logger.get_stdout_hndlr()
    stdout_hndlr.stream = outstr

    return out_window


def _cleanup_output():
    sys.stdout = None
    stdout_hndlr = logger.get_stdout_hndlr()
    stdout_hndlr.stream = None


# -----------------------------------------------------------------------------
# Functions related to creating/loading a new pyRevit session
# -----------------------------------------------------------------------------
def _check_autoupdate_inprogress():
    return envvars.get_pyrevit_env_var(
        loadertypes.EnvDictionaryKeys.autoupdating
        )


def _set_autoupdate_inprogress(state):
    envvars.set_pyrevit_env_var(
        loadertypes.EnvDictionaryKeys.autoupdating, state
        )


def _perform_onsessionload_ops():
    # clear the cached engines
    if not _clear_running_engines():
        mlogger.debug('No Engine Manager exists...')

    # check for updates
    if user_config.core.get_option('autoupdate', default_value=False) \
            and not _check_autoupdate_inprogress():
        mlogger.info('Auto-update is active. Attempting update...')
        _set_autoupdate_inprogress(True)
        updater.update_pyrevit()
        _set_autoupdate_inprogress(False)

    # once pre-load is complete, report environment conditions
    uuid_str = sessioninfo.new_session_uuid()
    sessioninfo.report_env()

    # reset the list of assemblies loaded under pyRevit session
    sessioninfo.set_loaded_pyrevit_assemblies([])

    # asking usagelog module to setup the usage logging system
    # (active or not active)
    usagelog.setup_usage_logfile(uuid_str)

    # apply Upgrades
    upgrade.upgrade_existing_pyrevit()


def _perform_onsessionloadcomplete_ops():
    # cleanup old assembly files.
    asmmaker.cleanup_assembly_files()

    # clean up temp app files between sessions.
    appdata.cleanup_appdata_folder()


def _new_session():
    """
    Get all installed extensions (UI extension only) and creates an assembly,
    and a ui for each.

    Returns:
        None
    """

    assembled_exts = []
    # get all installed ui extensions
    for ui_ext in extensionmgr.get_installed_ui_extensions():
        # configure extension components for metadata
        # e.g. liquid templates like {{author}}
        ui_ext.configure()

        # create a dll assembly and get assembly info
        ext_asm_info = asmmaker.create_assembly(ui_ext)
        if not ext_asm_info:
            mlogger.critical('Failed to create assembly for: %s', ui_ext)
            continue
        else:
            mlogger.info('Extension assembly created: %s', ui_ext.name)

        assembled_exts.append(
            AssembledExtension(ext=ui_ext, assm=ext_asm_info)
        )

    # add names of the created assemblies to the session info
    sessioninfo.set_loaded_pyrevit_assemblies(
        [x.assm.name for x in assembled_exts]
    )

    # run startup scripts for this ui extension, if any
    for assm_ext in assembled_exts:
        if assm_ext.ext.startup_script:
            # build syspaths for the startup script
            sys_paths = [assm_ext.ext.directory]
            if assm_ext.ext.library_path:
                sys_paths.insert(0, assm_ext.ext.library_path)

            mlogger.info('Running startup tasks for %s', assm_ext.ext.name)
            mlogger.debug('Executing startup script for extension: %s',
                          assm_ext.ext.name)

            # now run
            execute_script(
                assm_ext.ext.startup_script,
                sys_paths=sys_paths
                )

    # update/create ui (needs the assembly to link button actions
    # to commands saved in the dll)
    for assm_ext in assembled_exts:
        uimaker.update_pyrevit_ui(
            assm_ext.ext,
            assm_ext.assm,
            user_config.core.get_option('loadbeta',
                                        default_value=False)
        )
        mlogger.info('UI created for extension: %s', assm_ext.ext.name)

    # re-sort the ui elements
    for assm_ext in assembled_exts:
        uimaker.sort_pyrevit_ui(assm_ext.ext)

    # cleanup existing UI. This is primarily for cleanups after reloading
    uimaker.cleanup_pyrevit_ui()


def load_session():
    """Handles loading/reloading of the pyRevit addin and extensions.
    To create a proper ui, pyRevit extensions needs to be properly parsed and
    a dll assembly needs to be created. This function handles these tasks
    through interactions with .extensions, .loader.asmmaker, and .loader.uimaker

    Example:
        >>> from pyrevit.loader.sessionmgr import load_session
        >>> load_session()     # start loading a new pyRevit session

    Returns:
        None
    """
    # setup runtime environment variables
    sessioninfo.setup_runtime_vars()

    # the loader dll addon, does not create an output window
    # if an output window is not provided, create one
    if EXEC_PARAMS.first_load:
        output_window = _setup_output()
    else:
        from pyrevit import script
        output_window = script.get_output()

    # initialize timer to measure load time
    timer = Timer()

    # perform pre-load tasks
    _perform_onsessionload_ops()

    # create a new session
    _new_session()

    # perform post-load tasks
    _perform_onsessionloadcomplete_ops()

    # log load time and thumbs-up :)
    endtime = timer.get_time()
    success_emoji = ':OK_hand:' if endtime < 3.00 else ':thumbs_up:'
    mlogger.info('Load time: %s seconds %s', endtime, success_emoji)

    # if everything went well, self destruct
    try:
        timeout = user_config.core.startuplogtimeout
        if timeout > 0 and not logger.loggers_have_errors():
            if EXEC_PARAMS.first_load:
                # output_window is of type ScriptOutput
                output_window.SelfDestructTimer(timeout)
            else:
                # output_window is of type PyRevitOutputWindow
                output_window.self_destruct(timeout)
    except Exception as imp_err:
        mlogger.error('Error setting up self_destruct on output window | %s',
                      imp_err)

    _cleanup_output()


def reload_pyrevit():
    mlogger.info('Reloading....')
    load_session()

# -----------------------------------------------------------------------------
# Functions related to finding/executing
# pyrevit command or script in current session
# -----------------------------------------------------------------------------
class PyRevitExternalCommandType(object):
    def __init__(self, extcmd_type, extcmd_availtype):
        self._extcmd_type = extcmd_type
        self._extcmd = extcmd_type()
        if extcmd_availtype:
            self._extcmd_availtype = extcmd_availtype
            self._extcmd_avail = extcmd_availtype()
        else:
            self._extcmd_availtype = None
            self._extcmd_avail = None

    @property
    def extcmd_type(self):
        return self._extcmd_type

    @property
    def typename(self):
        return self._extcmd_type.FullName

    @property
    def extcmd_availtype(self):
        return self._extcmd_availtype

    @property
    def avail_typename(self):
        return self._extcmd_availtype.FullName

    @property
    def script(self):
        return getattr(self._extcmd, 'baked_scriptSource', None)

    @property
    def alternate_script(self):
        return getattr(self._extcmd, 'baked_alternateScriptSource', None)

    @property
    def syspaths(self):
        return getattr(self._extcmd, 'baked_syspaths', None)

    @property
    def helpsource(self):
        return getattr(self._extcmd, 'baked_helpSource', None)

    @property
    def name(self):
        return getattr(self._extcmd, 'baked_cmdName', None)

    @property
    def bundle(self):
        return getattr(self._extcmd, 'baked_cmdBundle', None)

    @property
    def extension(self):
        return getattr(self._extcmd, 'baked_cmdExtension', None)

    @property
    def unique_id(self):
        return getattr(self._extcmd, 'baked_cmdUniqueName', None)

    @property
    def needs_clean_engine(self):
        return getattr(self._extcmd, 'baked_needsCleanEngine', None)

    @property
    def needs_fullframe_engine(self):
        return getattr(self._extcmd, 'baked_needsFullFrameEngine', None)

    def is_available(self, category_set, zerodoc=False):
        if self._extcmd_availtype:
            return self._extcmd_avail.IsCommandAvailable(HOST_APP.uiapp,
                                                         category_set)
        elif not zerodoc:
            return True

        return False


pyrevit_extcmdtype_cache = []


def find_all_commands(category_set=None, cache=True):
    global pyrevit_extcmdtype_cache    #pylint: disable=W0603
    if cache and pyrevit_extcmdtype_cache:    #pylint: disable=E0601
        pyrevit_extcmds = pyrevit_extcmdtype_cache
    else:
        pyrevit_extcmds = []
        for loaded_assm_name in sessioninfo.get_loaded_pyrevit_assemblies():
            loaded_assm = coreutils.find_loaded_asm(loaded_assm_name)
            if loaded_assm:
                all_exported_types = loaded_assm[0].GetTypes()

                for pyrvt_type in all_exported_types:
                    tname = pyrvt_type.FullName
                    availtname = pyrvt_type.Name \
                                 + COMMAND_AVAILABILITY_NAME_POSTFIX
                    pyrvt_availtype = None

                    if not tname.endswith(COMMAND_AVAILABILITY_NAME_POSTFIX)\
                            and LOADER_BASE_NAMESPACE not in tname:
                        for exported_type in all_exported_types:
                            if exported_type.Name == availtname:
                                pyrvt_availtype = exported_type

                        pyrevit_extcmds.append(
                            PyRevitExternalCommandType(pyrvt_type,
                                                       pyrvt_availtype)
                            )
        if cache:
            pyrevit_extcmdtype_cache = pyrevit_extcmds

    # now check commands in current context if requested
    if category_set:
        return [x for x in pyrevit_extcmds
                if x.is_available(category_set=category_set,
                                  zerodoc=HOST_APP.uidoc is None)]
    else:
        return pyrevit_extcmds


def find_all_available_commands(use_current_context=True, cache=True):
    if use_current_context:
        cset = revit.get_selection_category_set()
    else:
        cset = None

    return find_all_commands(category_set=cset, cache=cache)


def find_pyrevitcmd(pyrevitcmd_unique_id):
    """Searches the pyRevit-generated assemblies under current session for
    the command with the matching unique name (class name) and returns the
    command type. Notice that this returned value is a 'type' and should be
    instantiated before use.

    Example:
        >>> cmd = find_pyrevitcmd('pyRevitCorepyRevitpyRevittoolsReload')
        >>> command_instance = cmd()
        >>> command_instance.Execute() # Provide commandData, message, elements

    Args:
        pyrevitcmd_unique_id (str): Unique name for the command

    Returns:
        Type for the command with matching unique name
    """
    # go through assmebles loaded under current pyRevit session
    # and try to find the command
    mlogger.debug('Searching for pyrevit command: %s', pyrevitcmd_unique_id)
    for loaded_assm_name in sessioninfo.get_loaded_pyrevit_assemblies():
        mlogger.debug('Expecting assm: %s', loaded_assm_name)
        loaded_assm = coreutils.find_loaded_asm(loaded_assm_name)
        if loaded_assm:
            mlogger.debug('Found assm: %s', loaded_assm_name)
            for pyrvt_type in loaded_assm[0].GetTypes():
                mlogger.debug('Found Type: %s', pyrvt_type)
                if pyrvt_type.FullName == pyrevitcmd_unique_id:
                    mlogger.debug('Found pyRevit command in %s',
                                  loaded_assm_name)
                    return pyrvt_type
            mlogger.debug('Could not find pyRevit command.')
        else:
            mlogger.debug('Can not find assm: %s', loaded_assm_name)

    return None


def create_tmp_commanddata():
    tmp_cmd_data = \
        FormatterServices.GetUninitializedObject(UI.ExternalCommandData)
    tmp_cmd_data.Application = HOST_APP.uiapp
    # tmp_cmd_data.IsReadOnly = False
    # tmp_cmd_data.View = None
    # tmp_cmd_data.JournalData = None
    return tmp_cmd_data


def execute_command_cls(extcmd_type, arguments=None,
                        clean_engine=False, fullframe_engine=False,
                        alternate_mode=False):

    command_instance = extcmd_type()
    # this is a manual execution from python code and not by user
    command_instance.executedFromUI = False
    # pass the arguments to the instance
    if arguments:
        command_instance.argumentList = Array[str](arguments)
    # force using clean engine
    command_instance.baked_needsCleanEngine = clean_engine
    # force using fullframe engine
    command_instance.baked_needsFullFrameEngine = fullframe_engine
    # force using the alternate script
    command_instance.altScriptModeOverride = alternate_mode

    re = command_instance.Execute(create_tmp_commanddata(),
                                  '',
                                  DB.ElementSet())
    command_instance = None
    return re


def execute_command(pyrevitcmd_unique_id):
    """Executes a pyRevit command.

    Args:
        pyrevitcmd_unique_id (str): Unique/Class Name of the pyRevit command

    Returns:
        results from the executed command
    """

    cmd_class = find_pyrevitcmd(pyrevitcmd_unique_id)

    if not cmd_class:
        mlogger.error('Can not find command with unique name: %s',
                      pyrevitcmd_unique_id)
        return None
    else:
        execute_command_cls(cmd_class)


def execute_script(script_path, arguments=None, sys_paths=None,
                   clean_engine=True, fullframe_engine=True):
    """Executes a script using pyRevit script executor.

    Args:
        script_path (str): Address of the script file

    Returns:
        results dictionary from the executed script
    """

    from pyrevit import MAIN_LIB_DIR, MISC_LIB_DIR
    from pyrevit.coreutils import DEFAULT_SEPARATOR
    from pyrevit.framework import clr

    executor = loadertypes.ScriptExecutor()
    script_name = op.basename(script_path)
    core_syspaths = [MAIN_LIB_DIR, MISC_LIB_DIR]
    if sys_paths:
        sys_paths.extend(core_syspaths)
    else:
        sys_paths = core_syspaths

    cmd_runtime = \
        loadertypes.PyRevitCommandRuntime(
            cmdData=create_tmp_commanddata(),
            elements=None,
            scriptSource=script_path,
            alternateScriptSource=None,
            syspaths=DEFAULT_SEPARATOR.join(sys_paths),
            arguments=arguments,
            helpSource=None,
            cmdName=script_name,
            cmdBundle=None,
            cmdExtension=None,
            cmdUniqueName=None,
            needsCleanEngine=clean_engine,
            needsFullFrameEngine=fullframe_engine,
            refreshEngine=False,
            forcedDebugMode=False,
            altScriptMode=False,
            executedFromUI=False
            )

    executor.ExecuteScript(
        clr.Reference[loadertypes.PyRevitCommandRuntime](cmd_runtime)
        )

    return cmd_runtime.GetResultsDictionary()
