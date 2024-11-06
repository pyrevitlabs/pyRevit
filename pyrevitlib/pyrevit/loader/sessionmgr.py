"""The loader module manages the workflow of loading a new pyRevit session.

Its main purpose is to orchestrate the process of finding pyRevit extensions,
creating dll assemblies for them, and creating a user interface
in the host application.

Everything starts from `sessionmgr.load_session()` function...

The only public function is `load_session()` that loads a new session.
Everything else is private.
"""
import sys
from collections import namedtuple

from pyrevit import EXEC_PARAMS, HOST_APP
from pyrevit import MAIN_LIB_DIR, MISC_LIB_DIR
from pyrevit import framework
from pyrevit.coreutils import Timer
from pyrevit.coreutils import assmutils
from pyrevit.coreutils import envvars
from pyrevit.coreutils import appdata
from pyrevit.coreutils import logger
from pyrevit.coreutils import applocales
from pyrevit.loader import sessioninfo
from pyrevit.loader import asmmaker
from pyrevit.loader import uimaker
from pyrevit.loader import hooks
from pyrevit.userconfig import user_config
from pyrevit.extensions import extensionmgr
from pyrevit.versionmgr import updater
from pyrevit.versionmgr import upgrade
from pyrevit import telemetry
from pyrevit import routes
# import the runtime first to get all the c-sharp code to compile
from pyrevit import runtime
from pyrevit.runtime import types as runtime_types
# now load the rest of module that could depend on the compiled runtime
from pyrevit import output

from pyrevit import DB, UI, revit


#pylint: disable=W0703,C0302,C0103,no-member
mlogger = logger.get_logger(__name__)


AssembledExtension = namedtuple('AssembledExtension', ['ext', 'assm'])


def _clear_running_engines():
    # clear the cached engines
    try:
        my_output = output.get_output()
        if my_output:
            my_output.close_others(all_open_outputs=True)

        runtime_types.ScriptEngineManager.ClearEngines(
            excludeEngine=EXEC_PARAMS.engine_id
            )
        return True
    except AttributeError:
        return False


def _setup_output():
    # create output window and assign handle
    out_window = runtime.types.ScriptConsole()
    runtime_info = sessioninfo.get_runtime_info()
    out_window.AppVersion = '{}:{}:{}'.format(
        runtime_info.pyrevit_version,
        int(runtime_info.engine_version),
        runtime_info.host_version
        )

    # create output stream and set stdout to it
    # we're not opening the output window here.
    # The output stream will open the window if anything is being printed.
    outstr = runtime.types.ScriptIO(out_window)
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
    return envvars.get_pyrevit_env_var(envvars.AUTOUPDATING_ENVVAR)


def _set_autoupdate_inprogress(state):
    envvars.set_pyrevit_env_var(envvars.AUTOUPDATING_ENVVAR, state)


def _perform_onsessionloadstart_ops():
    # clear the cached engines
    if not _clear_running_engines():
        mlogger.debug('No Engine Manager exists...')

    # check for updates
    if user_config.auto_update \
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

    # init executor
    runtime_types.ScriptExecutor.Initialize()

    # init routes
    routes.init()

    # asking telemetry module to setup the telemetry system
    # (active or not active)
    telemetry.setup_telemetry(uuid_str)

    # apply Upgrades
    upgrade.upgrade_existing_pyrevit()

    # setup hooks
    hooks.setup_hooks()


def _perform_onsessionloadcomplete_ops():
    # cleanup old assembly files.
    asmmaker.cleanup_assembly_files()

    # clean up temp app files between sessions.
    appdata.cleanup_appdata_folder()

    # activate hooks now
    hooks.activate()

    # activate internal handlers
    # toggle doc colorizer
    revit.tabs.init_doc_colorizer(user_config)

    # activate runtime routes server
    if user_config.routes_server:
        routes.active_routes_api()
        active_server = routes.activate_server()
        if active_server:
            mlogger.info(str(active_server))
        else:
            mlogger.error('Routes servers failed activation')


def _new_session():
    """Create an assembly and UI for each installed UI extensions."""
    assembled_exts = []
    # get all installed ui extensions
    for ui_ext in extensionmgr.get_installed_ui_extensions():
        # configure extension components for metadata
        # e.g. liquid templates like {{author}}
        ui_ext.configure()

        # collect all module references from extensions
        ui_ext_modules = []
        # FIXME: currently dlls inside bin/ are not pre-loaded since
        # this will lock them by Revit. Maybe all dlls should be loaded
        # from memory (read binary and load assembly)?
        # ui_ext_modules.extend(ui_ext.get_extension_modules())
        ui_ext_modules.extend(ui_ext.get_command_modules())
        # make sure they are all loaded
        assmutils.load_asm_files(ui_ext_modules)
        # and update env information
        sessioninfo.update_loaded_pyrevit_referenced_modules(ui_ext_modules)

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
            execute_extension_startup_script(
                assm_ext.ext.startup_script,
                assm_ext.ext.name,
                sys_paths=sys_paths
                )

    # register extension hooks
    for assm_ext in assembled_exts:
        hooks.register_hooks(assm_ext.ext)

    # update/create ui (needs the assembly to link button actions
    # to commands saved in the dll)
    for assm_ext in assembled_exts:
        uimaker.update_pyrevit_ui(
            assm_ext.ext,
            assm_ext.assm,
            user_config.load_beta
        )
        mlogger.info('UI created for extension: %s', assm_ext.ext.name)

    # re-sort the ui elements
    for assm_ext in assembled_exts:
        uimaker.sort_pyrevit_ui(assm_ext.ext)

    # cleanup existing UI. This is primarily for cleanups after reloading
    uimaker.cleanup_pyrevit_ui()

    # reflow the ui if requested, depending on the language direction
    if user_config.respect_language_direction:
        current_applocale = applocales.get_current_applocale()
        uimaker.reflow_pyrevit_ui(direction=current_applocale.lang_dir)
    else:
        uimaker.reflow_pyrevit_ui()


def load_session():
    """Handles loading/reloading of the pyRevit addin and extensions.

    To create a proper ui, pyRevit extensions needs to be properly parsed and
    a dll assembly needs to be created. This function handles these tasks
    through interactions with .extensions, .loader.asmmaker, and .loader.uimaker.

    Examples:
        ```python
        from pyrevit.loader.sessionmgr import load_session
        load_session()     # start loading a new pyRevit session
        ```

    Returns:
        (str): sesion uuid
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
    _perform_onsessionloadstart_ops()

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
        timeout = user_config.startuplog_timeout
        if timeout > 0 and not logger.loggers_have_errors():
            if EXEC_PARAMS.first_load:
                # output_window is of type ScriptConsole
                output_window.SelfDestructTimer(timeout)
            else:
                # output_window is of type PyRevitOutputWindow
                output_window.self_destruct(timeout)
    except Exception as imp_err:
        mlogger.error('Error setting up self_destruct on output window | %s',
                      imp_err)

    _cleanup_output()
    return sessioninfo.get_session_uuid()


def _perform_onsessionreload_ops():
    pass


def _perform_onsessionreloadcomplete_ops():
    pass


def reload_pyrevit():
    _perform_onsessionreload_ops()
    mlogger.info('Reloading....')
    session_Id = load_session()
    _perform_onsessionreloadcomplete_ops()
    return session_Id

# -----------------------------------------------------------------------------
# Functions related to finding/executing
# pyrevit command or script in current session
# -----------------------------------------------------------------------------
class PyRevitExternalCommandType(object):
    """PyRevit external command type."""
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
        return getattr(self._extcmd.ScriptData, 'ScriptPath', None)

    @property
    def config_script(self):
        return getattr(self._extcmd.ScriptData, 'ConfigScriptPath', None)

    @property
    def search_paths(self):
        value = getattr(self._extcmd.ScriptRuntimeConfigs, 'SearchPaths', [])
        return list(value)

    @property
    def arguments(self):
        value = getattr(self._extcmd.ScriptRuntimeConfigs, 'Arguments', [])
        return list(value)

    @property
    def engine_cfgs(self):
        return getattr(self._extcmd.ScriptRuntimeConfigs, 'EngineConfigs', '')

    @property
    def helpsource(self):
        return getattr(self._extcmd.ScriptData, 'HelpSource', None)

    @property
    def tooltip(self):
        return getattr(self._extcmd.ScriptData, 'Tooltip', None)

    @property
    def name(self):
        return getattr(self._extcmd.ScriptData, 'CommandName', None)

    @property
    def bundle(self):
        return getattr(self._extcmd.ScriptData, 'CommandBundle', None)

    @property
    def extension(self):
        return getattr(self._extcmd.ScriptData, 'CommandExtension', None)

    @property
    def unique_id(self):
        return getattr(self._extcmd.ScriptData, 'CommandUniqueId', None)

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
            loaded_assm = assmutils.find_loaded_asm(loaded_assm_name)
            if loaded_assm:
                all_exported_types = loaded_assm[0].GetTypes()

                for pyrvt_type in all_exported_types:
                    tname = pyrvt_type.FullName
                    availtname = pyrvt_type.Name \
                                 + runtime.CMD_AVAIL_NAME_POSTFIX
                    pyrvt_availtype = None

                    if not tname.endswith(runtime.CMD_AVAIL_NAME_POSTFIX)\
                            and runtime.RUNTIME_NAMESPACE not in tname:
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
    """Find a pyRevit command.

    Searches the pyRevit-generated assemblies under current session for
    the command with the matching unique name (class name) and returns the
    command type. Notice that this returned value is a 'type' and should be
    instantiated before use.

    Examples:
        ```python
        cmd = find_pyrevitcmd('pyRevitCorepyRevitpyRevittoolsReload')
        command_instance = cmd()
        command_instance.Execute() # Provide commandData, message, elements
        ```

    Args:
        pyrevitcmd_unique_id (str): Unique name for the command

    Returns:
        (type):Type for the command with matching unique name
    """
    # go through assmebles loaded under current pyRevit session
    # and try to find the command
    mlogger.debug('Searching for pyrevit command: %s', pyrevitcmd_unique_id)
    for loaded_assm_name in sessioninfo.get_loaded_pyrevit_assemblies():
        mlogger.debug('Expecting assm: %s', loaded_assm_name)
        loaded_assm = assmutils.find_loaded_asm(loaded_assm_name)
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
        framework.FormatterServices.GetUninitializedObject(
            UI.ExternalCommandData
            )
    tmp_cmd_data.Application = HOST_APP.uiapp
    # tmp_cmd_data.IsReadOnly = False
    # tmp_cmd_data.View = None
    # tmp_cmd_data.JournalData = None
    return tmp_cmd_data


def execute_command_cls(extcmd_type, arguments=None,
                        config_mode=False, exec_from_ui=False):

    command_instance = extcmd_type()
    # pass the arguments to the instance
    if arguments:
        command_instance.ScriptRuntimeConfigs.Arguments = \
            framework.List[str](arguments)
    # this is a manual execution from python code and not by user
    command_instance.ExecConfigs.MimicExecFromUI = exec_from_ui
    # force using the config script
    command_instance.ExecConfigs.UseConfigScript = config_mode

    # Execute(
    # ExternalCommandData commandData,
    # string message,
    # ElementSet elements
    # )
    re = command_instance.Execute(create_tmp_commanddata(),
                                  '',
                                  DB.ElementSet())
    command_instance = None
    return re


def execute_command(pyrevitcmd_unique_id):
    """Executes a pyRevit command.

    Args:
        pyrevitcmd_unique_id (str): Unique/Class Name of the pyRevit command
    """
    cmd_class = find_pyrevitcmd(pyrevitcmd_unique_id)

    if not cmd_class:
        mlogger.error('Can not find command with unique name: %s',
                      pyrevitcmd_unique_id)
        return None
    else:
        execute_command_cls(cmd_class)


def execute_extension_startup_script(script_path, ext_name, sys_paths=None):
    """Executes a script using pyRevit script executor.

    Args:
        script_path (str): Address of the script file
        ext_name (str): Name of the extension
        sys_paths (list): additional search paths
    """
    core_syspaths = [MAIN_LIB_DIR, MISC_LIB_DIR]
    if sys_paths:
        sys_paths.extend(core_syspaths)
    else:
        sys_paths = core_syspaths

    script_data = runtime.types.ScriptData()
    script_data.ScriptPath = script_path
    script_data.ConfigScriptPath = None
    script_data.CommandUniqueId = ''
    script_data.CommandName = 'Starting {}'.format(ext_name)
    script_data.CommandBundle = ''
    script_data.CommandExtension = ext_name
    script_data.HelpSource = ''

    script_runtime_cfg = runtime.types.ScriptRuntimeConfigs()
    script_runtime_cfg.CommandData = create_tmp_commanddata()
    script_runtime_cfg.SelectedElements = None
    script_runtime_cfg.SearchPaths = framework.List[str](sys_paths or [])
    script_runtime_cfg.Arguments = framework.List[str]([])
    script_runtime_cfg.EngineConfigs = \
        runtime.create_ipyengine_configs(
            clean=True,
            full_frame=True,
            persistent=True,
        )
    script_runtime_cfg.RefreshEngine = False
    script_runtime_cfg.ConfigMode = False
    script_runtime_cfg.DebugMode = False
    script_runtime_cfg.ExecutedFromUI = False

    runtime.types.ScriptExecutor.ExecuteScript(
        script_data,
        script_runtime_cfg
    )
