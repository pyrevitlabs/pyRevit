# encoding: utf-8
"""The loader module manages the workflow of loading a new pyRevit session.

Its main purpose is to orchestrate the process of finding pyRevit extensions,
creating dll assemblies for them, and creating a user interface
in the host application.

Everything starts from `sessionmgr.load_session()` function...

The only public function is `load_session()` that loads a new session.
Everything else is private.
"""
import sys
import time

from pyrevit import EXEC_PARAMS, HOST_APP
from pyrevit import framework
from pyrevit.coreutils import Timer
from pyrevit.coreutils import assmutils
from pyrevit.coreutils import envvars
from pyrevit.coreutils import logger
from pyrevit.loader import sessioninfo
from pyrevit.loader import hooks
from pyrevit.labs import PyRevit
from pyrevit.userconfig import user_config
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


# pylint: disable=W0703,C0302,C0103,no-member
mlogger = logger.get_logger(__name__)


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
    # route C#-side NLog messages into the session output window
    runtime_types.ScriptOutput.ConfigureLogging()
    # create the runtime-owned singleton output window and assign handle
    out = runtime_types.ScriptOutput.GetDefault()
    out_window = out.window
    # protect from close_other_outputs triggered by startup-script windows
    try:
        out.set_session_output(True)
    except Exception:
        pass
    runtime_info = sessioninfo.get_runtime_info()
    out_window.AppVersion = "{}:{}:{}".format(
        runtime_info.pyrevit_version,
        int(runtime_info.engine_version),
        runtime_info.host_version,
    )

    # create output stream and set stdout to it
    # we're not opening the output window here.
    # The output stream will open the window if anything is being printed.
    outstr = out.output_stream
    sys.stdout = outstr
    # sys.stderr = outstr


def _cleanup_output():
    try:
        runtime_types.ScriptOutput.GetDefault().set_session_output(False)
    except Exception:
        pass
    sys.stdout = None


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
        mlogger.debug("No Engine Manager exists...")

    # check for updates
    if user_config.auto_update and not _check_autoupdate_inprogress():
        mlogger.info("Auto-update is active. Attempting update...")
        _set_autoupdate_inprogress(True)
        updater.update_pyrevit()
        _set_autoupdate_inprogress(False)

    # once pre-load is complete, report environment conditions
    uuid_str = sessioninfo.new_session_uuid()
    sessioninfo.report_env()

    # reset the list of assemblies loaded under pyRevit session
    sessioninfo.set_loaded_pyrevit_assemblies([])

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
            mlogger.error("Routes servers failed activation")


def perform_preload():
    """Run pre-load session setup before the C# loader builds the UI.

    Invoked by the C# session orchestrator as the first step of a load. Sets up
    the session environment, output window, and pre-load services, and records
    the session start so perform_postload() can report load time.
    """
    # must run before setup_runtime_vars(), the first attachment consumer, so a
    # re-attached clone is picked up on reload
    PyRevit.PyRevitAttachments.ClearAttachmentCache()

    sessioninfo.setup_runtime_vars()

    # time from before output setup so the reported load time reflects the full
    # user wait, including first-load output window construction
    session_timer = Timer()
    envvars.set_pyrevit_env_var(envvars.SESSIONSTARTTIME_ENVVAR, session_timer.start)

    # always written, so a reload never reports the previous load's breakdown
    output_setup_time = None
    if EXEC_PARAMS.first_load:
        _setup_output()
        output_setup_time = session_timer.get_time()
    envvars.set_pyrevit_env_var(envvars.OUTPUTSETUPTIME_ENVVAR, output_setup_time)

    _perform_onsessionloadstart_ops()


def perform_postload():
    """Finalize the session after the C# loader has built the UI.

    Invoked by the C# session orchestrator as the last step of a load. Runs
    post-load services, registers the assemblies the C# loader produced, reports
    load time, and tears down the startup output stream.

    Returns:
        (str): session uuid
    """
    _perform_onsessionloadcomplete_ops()

    # so find_pyrevitcmd can locate commands the C# loader compiled
    _register_loaded_pyrevit_assemblies()

    starttime = envvars.get_pyrevit_env_var(envvars.SESSIONSTARTTIME_ENVVAR)
    if starttime is not None:
        endtime = time.time() - starttime
        success_emoji = ":OK_hand:" if endtime < 3.00 else ":thumbs_up:"
        mlogger.info("Load time: %s seconds %s", endtime, success_emoji)
        output_setup_time = envvars.get_pyrevit_env_var(envvars.OUTPUTSETUPTIME_ENVVAR)
        if output_setup_time is not None:
            mlogger.debug(
                "Load breakdown: output setup %.3fs | session build %.3fs",
                output_setup_time,
                endtime - output_setup_time,
            )

    # if everything went well, self destruct
    try:
        timeout = user_config.startuplog_timeout
        if timeout > 0 and not logger.loggers_have_errors():
            runtime_types.ScriptOutput.GetDefault().self_destruct(timeout)
    except Exception as imp_err:
        mlogger.error("Error setting up self_destruct on output window | %s", imp_err)

    _cleanup_output()
    return sessioninfo.get_session_uuid()


def _invoke_csharp_loadsession():
    """Invoke the C# session orchestrator and return the new session uuid.

    The C# entry (PyRevitLoaderApplication.LoadSession) runs the full sequence:
    perform_preload(), the C# UI build, then perform_postload().
    """
    loader_app_type = None
    for assembly in framework.AppDomain.CurrentDomain.GetAssemblies():
        try:
            if assembly.GetName().Name.startswith("pyRevitLoader"):
                loader_app_type = assembly.GetType(
                    "PyRevitLoader.PyRevitLoaderApplication"
                )
                if loader_app_type:
                    break
        except Exception:
            continue

    if not loader_app_type:
        mlogger.error("PyRevitLoaderApplication not found in loaded assemblies")
        return None

    load_session_method = loader_app_type.GetMethod("LoadSession")
    if not load_session_method:
        mlogger.error("LoadSession method not found in PyRevitLoaderApplication")
        return None

    mlogger.info("Loading session using C# LoadSession method...")
    load_session_method.Invoke(None, None)
    return sessioninfo.get_session_uuid()


def _register_loaded_pyrevit_assemblies():
    """Find and register pyRevit assemblies loaded by the C# session manager.

    Scans all loaded assemblies in the AppDomain to find pyRevit extension assemblies.
    Note: .NET cannot unload assemblies, so count may include old assemblies from
    previous reloads - this is expected behavior.
    """
    pyrevit_assemblies = []

    for assembly in framework.AppDomain.CurrentDomain.GetAssemblies():
        try:
            assembly_name = assembly.GetName().Name
            if assembly_name and assembly_name.startswith("pyRevit_"):
                pyrevit_assemblies.append(assembly_name)
                mlogger.debug("Found pyRevit assembly: %s", assembly_name)
        except Exception:
            continue

    if pyrevit_assemblies:
        sessioninfo.set_loaded_pyrevit_assemblies(pyrevit_assemblies)
        # mlogger.info('Registered %d pyRevit assemblies', len(pyrevit_assemblies))
    else:
        mlogger.warning("No pyRevit assemblies found")


def load_session():
    """Handles loading/reloading of the pyRevit addin and extensions.

    Delegates to the C# session orchestrator, which drives the full load:
    perform_preload(), the C# assembly/UI build, then perform_postload(). This
    is the entry used for reloads; the initial Revit startup invokes the C#
    orchestrator directly.

    Examples:
        ```python
        from pyrevit.loader.sessionmgr import load_session
        load_session()     # start loading a new pyRevit session
        ```

    Returns:
        (str): session uuid
    """
    return _invoke_csharp_loadsession()


def reload_pyrevit():
    mlogger.info("Reloading....")
    return load_session()


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
        return getattr(self._extcmd.ScriptData, "ScriptPath", None)

    @property
    def config_script(self):
        return getattr(self._extcmd.ScriptData, "ConfigScriptPath", None)

    @property
    def search_paths(self):
        value = getattr(self._extcmd.ScriptRuntimeConfigs, "SearchPaths", [])
        return list(value)

    @property
    def arguments(self):
        value = getattr(self._extcmd.ScriptRuntimeConfigs, "Arguments", [])
        return list(value)

    @property
    def engine_cfgs(self):
        return getattr(self._extcmd.ScriptRuntimeConfigs, "EngineConfigs", "")

    @property
    def helpsource(self):
        return getattr(self._extcmd.ScriptData, "HelpSource", None)

    @property
    def tooltip(self):
        return getattr(self._extcmd.ScriptData, "Tooltip", None)

    @property
    def name(self):
        return getattr(self._extcmd.ScriptData, "CommandName", None)

    @property
    def bundle(self):
        return getattr(self._extcmd.ScriptData, "CommandBundle", None)

    @property
    def extension(self):
        return getattr(self._extcmd.ScriptData, "CommandExtension", None)

    @property
    def unique_id(self):
        return getattr(self._extcmd.ScriptData, "CommandUniqueId", None)

    @property
    def control_id(self):
        return getattr(self._extcmd.ScriptData, "CommandControlId", None)

    def is_available(self, category_set, zerodoc=False):
        if self._extcmd_availtype:
            return self._extcmd_avail.IsCommandAvailable(HOST_APP.uiapp, category_set)
        elif not zerodoc:
            return True

        return False


pyrevit_extcmdtype_cache = []


def find_all_commands(category_set=None, cache=True):
    global pyrevit_extcmdtype_cache  # pylint: disable=W0603
    if cache and pyrevit_extcmdtype_cache:  # pylint: disable=E0601
        pyrevit_extcmds = pyrevit_extcmdtype_cache
    else:
        pyrevit_extcmds = []
        for loaded_assm_name in sessioninfo.get_loaded_pyrevit_assemblies():
            loaded_assm = assmutils.find_loaded_asm(loaded_assm_name)
            if loaded_assm:
                all_exported_types = loaded_assm[0].GetTypes()

                for pyrvt_type in all_exported_types:
                    tname = pyrvt_type.FullName
                    availtname = pyrvt_type.Name + runtime.CMD_AVAIL_NAME_POSTFIX
                    pyrvt_availtype = None

                    if (
                        not tname.endswith(runtime.CMD_AVAIL_NAME_POSTFIX)
                        and runtime.RUNTIME_NAMESPACE not in tname
                        and pyrvt_type.IsSubclassOf(runtime.CMD_EXECUTOR_TYPE)
                    ):
                        for exported_type in all_exported_types:
                            if exported_type.Name == availtname:
                                pyrvt_availtype = exported_type

                        pyrevit_extcmds.append(
                            PyRevitExternalCommandType(pyrvt_type, pyrvt_availtype)
                        )
        if cache:
            pyrevit_extcmdtype_cache = pyrevit_extcmds

    # now check commands in current context if requested
    if category_set:
        return [
            x
            for x in pyrevit_extcmds
            if x.is_available(category_set=category_set, zerodoc=HOST_APP.uidoc is None)
        ]
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
        cmd = find_pyrevitcmd('pyrevitcore_pyrevit_pyrevit_tools_reload')
        command_instance = cmd()
        command_instance.Execute() # Provide commandData, message, elements
        ```

    Args:
        pyrevitcmd_unique_id (str): Unique name for the command

    Returns:
        (type):Type for the command with matching unique name
    """
    def _normalize_lookup_id(value):
        if not value:
            return ""

        normalized = []
        for char in str(value).lower():
            normalized.append(char if char.isalnum() else "_")

        if normalized and normalized[0].isdigit():
            normalized.insert(0, "_")

        return "".join(normalized)

    lookup_id = _normalize_lookup_id(pyrevitcmd_unique_id)

    # go through assmebles loaded under current pyRevit session
    # and try to find the command
    mlogger.debug("Searching for pyrevit command: %s", pyrevitcmd_unique_id)
    for loaded_assm_name in sessioninfo.get_loaded_pyrevit_assemblies():
        mlogger.debug("Expecting assm: %s", loaded_assm_name)
        loaded_assm = assmutils.find_loaded_asm(loaded_assm_name)
        if loaded_assm:
            mlogger.debug("Found assm: %s", loaded_assm_name)
            for pyrvt_type in loaded_assm[0].GetTypes():
                mlogger.debug("Found Type: %s", pyrvt_type)
                if pyrvt_type.FullName == pyrevitcmd_unique_id \
                        or pyrvt_type.Name == pyrevitcmd_unique_id \
                        or _normalize_lookup_id(pyrvt_type.FullName) == lookup_id \
                        or _normalize_lookup_id(pyrvt_type.Name) == lookup_id:
                    mlogger.debug("Found pyRevit command in %s", loaded_assm_name)
                    return pyrvt_type
            mlogger.debug("Could not find pyRevit command.")
        else:
            mlogger.debug("Can not find assm: %s", loaded_assm_name)

    return None


def create_tmp_commanddata():
    tmp_cmd_data = framework.FormatterServices.GetUninitializedObject(
        UI.ExternalCommandData
    )
    tmp_cmd_data.Application = HOST_APP.uiapp
    # tmp_cmd_data.IsReadOnly = False
    # tmp_cmd_data.View = None
    # tmp_cmd_data.JournalData = None
    return tmp_cmd_data


def execute_command_cls(
    extcmd_type, arguments=None, config_mode=False, exec_from_ui=True
):

    command_instance = extcmd_type()
    # pass the arguments to the instance
    if arguments:
        command_instance.ScriptRuntimeConfigs.Arguments = framework.List[str](arguments)
    # this is a manual execution from python code and not by user
    command_instance.ExecConfigs.MimicExecFromUI = exec_from_ui
    # force using the config script
    command_instance.ExecConfigs.UseConfigScript = config_mode

    # Execute(
    # ExternalCommandData commandData,
    # string message,
    # ElementSet elements
    # )
    re = command_instance.Execute(create_tmp_commanddata(), "", DB.ElementSet())
    command_instance = None
    return re


def execute_command(pyrevitcmd_unique_id):
    """Executes a pyRevit command.

    Args:
        pyrevitcmd_unique_id (str): Unique/Class Name of the pyRevit command
    """
    cmd_class = find_pyrevitcmd(pyrevitcmd_unique_id)

    if not cmd_class:
        mlogger.error("Can not find command with unique name: %s", pyrevitcmd_unique_id)
        return None
    else:
        execute_command_cls(cmd_class)
