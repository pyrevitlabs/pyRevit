"""Handle reading and parsing, writing and saving of all user configurations.

This module handles the reading and writing of the pyRevit configuration files.
It's been used extensively by pyRevit sub-modules. user_config is
set up automatically in the global scope by this module and can be imported
into scripts and other modules to access the default configurations.

All other modules use this module to query user config.

Examples:
    ```python
    from pyrevit.userconfig import user_config
    user_config.add_section('newsection')
    user_config.newsection.property = value
    user_config.newsection.get_option('property', default_value)
    user_config.save_changes()
    ```


The user_config object is also the destination for reading and writing
configuration by pyRevit scripts through :func:`get_config` of
:mod:`pyrevit.script` module. Here is the function source:

.. literalinclude:: ../../pyrevitlib/pyrevit/script.py
    :pyobject: get_config

Examples:
    ```python
    from pyrevit import script
    cfg = script.get_config()
    cfg.property = value
    cfg.get_option('property', default_value)
    script.save_config()
    ```
"""
#pylint: disable=C0103,C0413,W0703
import os
import os.path as op

from pyrevit import EXEC_PARAMS, HOME_DIR, HOST_APP
from pyrevit import PyRevitException
from pyrevit import EXTENSIONS_DEFAULT_DIR, THIRDPARTY_EXTENSIONS_DEFAULT_DIR
from pyrevit import PYREVIT_ALLUSER_APP_DIR, PYREVIT_APP_DIR
from pyrevit.compat import winreg as wr

from pyrevit.labs import PyRevit

from pyrevit import coreutils
from pyrevit.coreutils import appdata
from pyrevit.coreutils import configparser
from pyrevit.coreutils import logger
from pyrevit.versionmgr import upgrade
# pylint: disable=C0103,C0413,W0703
DEFAULT_CSV_SEPARATOR = ','


mlogger = logger.get_logger(__name__)


CONSTS = PyRevit.PyRevitConsts


class PyRevitConfig(configparser.PyRevitConfigParser):
    """Provide read/write access to pyRevit configuration.

    Args:
        cfg_file_path (str): full path to config file to be used.
        config_type (str): type of config file

    Examples:
        ```python
        cfg = PyRevitConfig(cfg_file_path)
        cfg.add_section('sectionname')
        cfg.sectionname.property = value
        cfg.sectionname.get_option('property', default_value)
        cfg.save_changes()
        ```
    """

    def __init__(self, cfg_file_path=None, config_type='Unknown'):
        """Load settings from provided config file and setup parser."""
        # try opening and reading config file in order.
        super(PyRevitConfig, self).__init__(cfg_file_path=cfg_file_path)

        # set log mode on the logger module based on
        # user settings (overriding the defaults)
        self._update_env()
        self._admin = config_type == 'Admin'
        self.config_type = config_type

    def _update_env(self):
        # update the debug level based on user config
        mlogger.reset_level()

        try:
            # first check to see if command is not in forced debug mode
            if not EXEC_PARAMS.debug_mode:
                if self.core.debug:
                    mlogger.set_debug_mode()
                    mlogger.debug('Debug mode is enabled in user settings.')
                elif self.core.verbose:
                    mlogger.set_verbose_mode()

            logger.set_file_logging(self.core.filelogging)
        except Exception as env_update_err:
            mlogger.debug('Error updating env variable per user config. | %s',
                          env_update_err)

    @property
    def config_file(self):
        """Current config file path."""
        return self._cfg_file_path

    @property
    def environment(self):
        """Environment section."""
        if not self.has_section(CONSTS.EnvConfigsSectionName):
            self.add_section(CONSTS.EnvConfigsSectionName)
        return self.get_section(CONSTS.EnvConfigsSectionName)

    @property
    def core(self):
        """Core section."""
        if not self.has_section(CONSTS.ConfigsCoreSection):
            self.add_section(CONSTS.ConfigsCoreSection)
        return self.get_section(CONSTS.ConfigsCoreSection)

    @property
    def routes(self):
        """Routes section."""
        if not self.has_section(CONSTS.ConfigsRoutesSection):
            self.add_section(CONSTS.ConfigsRoutesSection)
        return self.get_section(CONSTS.ConfigsRoutesSection)

    @property
    def telemetry(self):
        """Telemetry section."""
        if not self.has_section(CONSTS.ConfigsTelemetrySection):
            self.add_section(CONSTS.ConfigsTelemetrySection)
        return self.get_section(CONSTS.ConfigsTelemetrySection)

    @property
    def bin_cache(self):
        """"Whether to use the cache for extensions."""
        return self.core.get_option(
            CONSTS.ConfigsBinaryCacheKey,
            default_value=CONSTS.ConfigsBinaryCacheDefault,
        )

    @bin_cache.setter
    def bin_cache(self, state):
        self.core.set_option(
            CONSTS.ConfigsBinaryCacheKey,
            value=state
        )

    @property
    def check_updates(self):
        """Whether to check for updates."""
        return self.core.get_option(
            CONSTS.ConfigsCheckUpdatesKey,
            default_value=CONSTS.ConfigsCheckUpdatesDefault,
        )

    @check_updates.setter
    def check_updates(self, state):
        self.core.set_option(
            CONSTS.ConfigsCheckUpdatesKey,
            value=state
        )

    @property
    def auto_update(self):
        """Whether to automatically update pyRevit."""
        return self.core.get_option(
            CONSTS.ConfigsAutoUpdateKey,
            default_value=CONSTS.ConfigsAutoUpdateDefault,
        )

    @auto_update.setter
    def auto_update(self, state):
        self.core.set_option(
            CONSTS.ConfigsAutoUpdateKey,
            value=state
        )

    @property
    def rocket_mode(self):
        """Whether to enable rocket mode."""
        return self.core.get_option(
            CONSTS.ConfigsRocketModeKey,
            default_value=CONSTS.ConfigsRocketModeDefault,
        )

    @rocket_mode.setter
    def rocket_mode(self, state):
        self.core.set_option(
            CONSTS.ConfigsRocketModeKey,
            value=state
        )

    @property
    def log_level(self):
        """Logging level."""
        if self.core.get_option(
                CONSTS.ConfigsDebugKey,
                default_value=CONSTS.ConfigsDebugDefault,
            ):
            return PyRevit.PyRevitLogLevels.Debug
        elif self.core.get_option(
                CONSTS.ConfigsVerboseKey,
                default_value=CONSTS.ConfigsVerboseDefault,
            ):
            return PyRevit.PyRevitLogLevels.Verbose
        return PyRevit.PyRevitLogLevels.Quiet

    @log_level.setter
    def log_level(self, state):
        if state == PyRevit.PyRevitLogLevels.Debug:
            self.core.set_option(CONSTS.ConfigsDebugKey, True)
            self.core.set_option(CONSTS.ConfigsVerboseKey, True)
        elif state == PyRevit.PyRevitLogLevels.Verbose:
            self.core.set_option(CONSTS.ConfigsDebugKey, False)
            self.core.set_option(CONSTS.ConfigsVerboseKey, True)
        else:
            self.core.set_option(CONSTS.ConfigsDebugKey, False)
            self.core.set_option(CONSTS.ConfigsVerboseKey, False)

    @property
    def file_logging(self):
        """Whether to enable file logging."""
        return self.core.get_option(
            CONSTS.ConfigsFileLoggingKey,
            default_value=CONSTS.ConfigsFileLoggingDefault,
        )

    @file_logging.setter
    def file_logging(self, state):
        self.core.set_option(
            CONSTS.ConfigsFileLoggingKey,
            value=state
        )

    @property
    def startuplog_timeout(self):
        """Timeout for the startup log."""
        return self.core.get_option(
            CONSTS.ConfigsStartupLogTimeoutKey,
            default_value=CONSTS.ConfigsStartupLogTimeoutDefault,
        )

    @startuplog_timeout.setter
    def startuplog_timeout(self, timeout):
        self.core.set_option(
            CONSTS.ConfigsStartupLogTimeoutKey,
            value=timeout
        )

    @property
    def required_host_build(self):
        """Host build required to run the commands."""
        return self.core.get_option(
            CONSTS.ConfigsRequiredHostBuildKey,
            default_value="",
        )

    @required_host_build.setter
    def required_host_build(self, buildnumber):
        self.core.set_option(
            CONSTS.ConfigsRequiredHostBuildKey,
            value=buildnumber
        )

    @property
    def min_host_drivefreespace(self):
        """Minimum free space for running the commands."""
        return self.core.get_option(
            CONSTS.ConfigsMinDriveSpaceKey,
            default_value=CONSTS.ConfigsMinDriveSpaceDefault,
        )

    @min_host_drivefreespace.setter
    def min_host_drivefreespace(self, freespace):
        self.core.set_option(
            CONSTS.ConfigsMinDriveSpaceKey,
            value=freespace
        )

    @property
    def load_beta(self):
        """Whether to load commands in beta."""
        return self.core.get_option(
            CONSTS.ConfigsLoadBetaKey,
            default_value=CONSTS.ConfigsLoadBetaDefault,
        )

    @load_beta.setter
    def load_beta(self, state):
        self.core.set_option(
            CONSTS.ConfigsLoadBetaKey,
            value=state
        )

    @property
    def output_close_others(self):
        """Whether to close other output windows."""
        return self.core.get_option(
            CONSTS.ConfigsCloseOtherOutputsKey,
            default_value=CONSTS.ConfigsCloseOtherOutputsDefault,
        )

    @output_close_others.setter
    def output_close_others(self, state):
        self.core.set_option(
            CONSTS.ConfigsCloseOtherOutputsKey,
            value=state
        )

    @property
    def output_close_mode_enum(self):
        """Output window closing mode as enum (CurrentCommand | CloseAll)."""
        value = self.core.get_option(
            CONSTS.ConfigsCloseOutputModeKey,
            default_value=CONSTS.ConfigsCloseOutputModeDefault,
        )
        if not value:
            value = CONSTS.ConfigsCloseOutputModeDefault

        value_lc = str(value).lower()

        if value_lc == str(CONSTS.ConfigsCloseOutputModeCloseAll).lower():
            return PyRevit.OutputCloseMode.CloseAll
        else:
            return PyRevit.OutputCloseMode.CurrentCommand

    @output_close_mode_enum.setter
    def output_close_mode_enum(self, mode):
        """Store string in INI, mapped from enum."""
        if mode == PyRevit.OutputCloseMode.CloseAll:
            self.core.set_option(
                CONSTS.ConfigsCloseOutputModeKey,
                value=CONSTS.ConfigsCloseOutputModeCloseAll
            )
        else:
            self.core.set_option(
                CONSTS.ConfigsCloseOutputModeKey,
                value=CONSTS.ConfigsCloseOutputModeCurrentCommand
            )

    @property
    def cpython_engine_version(self):
        """CPython engine version to use."""
        return self.core.get_option(
            CONSTS.ConfigsCPythonEngineKey,
            default_value=CONSTS.ConfigsCPythonEngineDefault,
        )

    @cpython_engine_version.setter
    def cpython_engine_version(self, version):
        self.core.set_option(
            CONSTS.ConfigsCPythonEngineKey,
            value=int(version)
        )

    @property
    def user_locale(self):
        """User locale."""
        return self.core.get_option(
            CONSTS.ConfigsLocaleKey,
            default_value="",
        )

    @user_locale.setter
    def user_locale(self, local_code):
        self.core.set_option(
            CONSTS.ConfigsLocaleKey,
            value=local_code
        )

    @property
    def output_stylesheet(self):
        """Stylesheet used for output."""
        return self.core.get_option(
            CONSTS.ConfigsOutputStyleSheet,
            default_value="",
        )

    @output_stylesheet.setter
    def output_stylesheet(self, stylesheet_filepath):
        if stylesheet_filepath:
            self.core.set_option(
                CONSTS.ConfigsOutputStyleSheet,
                value=stylesheet_filepath
            )
        else:
            self.core.remove_option(CONSTS.ConfigsOutputStyleSheet)

    @property
    def routes_host(self):
        """Routes API host."""
        return self.routes.get_option(
            CONSTS.ConfigsRoutesHostKey,
            default_value=CONSTS.ConfigsRoutesHostDefault,
        )

    @routes_host.setter
    def routes_host(self, routes_host):
        self.routes.set_option(
            CONSTS.ConfigsRoutesHostKey,
            value=routes_host
        )

    @property
    def routes_port(self):
        """API routes port."""
        return self.routes.get_option(
            CONSTS.ConfigsRoutesPortKey,
            default_value=CONSTS.ConfigsRoutesPortDefault,
        )

    @routes_port.setter
    def routes_port(self, port):
        self.routes.set_option(
            CONSTS.ConfigsRoutesPortKey,
            value=port
        )

    @property
    def load_core_api(self):
        """Whether to load pyRevit core api."""
        return self.routes.get_option(
            CONSTS.ConfigsLoadCoreAPIKey,
            default_value=CONSTS.ConfigsConfigsLoadCoreAPIDefault,
        )

    @load_core_api.setter
    def load_core_api(self, state):
        self.routes.set_option(
            CONSTS.ConfigsLoadCoreAPIKey,
            value=state
        )

    @property
    def telemetry_utc_timestamp(self):
        """Whether to use UTC timestamps in telemetry."""
        return self.telemetry.get_option(
            CONSTS.ConfigsTelemetryUTCTimestampsKey,
            default_value=CONSTS.ConfigsTelemetryUTCTimestampsDefault,
        )

    @telemetry_utc_timestamp.setter
    def telemetry_utc_timestamp(self, state):
        self.telemetry.set_option(
            CONSTS.ConfigsTelemetryUTCTimestampsKey,
            value=state
        )

    @property
    def telemetry_status(self):
        """Telemetry status."""
        return self.telemetry.get_option(
            CONSTS.ConfigsTelemetryStatusKey,
            default_value=CONSTS.ConfigsTelemetryStatusDefault,
        )

    @telemetry_status.setter
    def telemetry_status(self, state):
        self.telemetry.set_option(
            CONSTS.ConfigsTelemetryStatusKey,
            value=state
        )

    @property
    def telemetry_file_dir(self):
        """Telemetry file directory."""
        return self.telemetry.get_option(
            CONSTS.ConfigsTelemetryFileDirKey,
            default_value="",
        )

    @telemetry_file_dir.setter
    def telemetry_file_dir(self, filepath):
        self.telemetry.set_option(
            CONSTS.ConfigsTelemetryFileDirKey,
            value=filepath
        )

    @property
    def telemetry_server_url(self):
        """Telemetry server URL."""
        return self.telemetry.get_option(
            CONSTS.ConfigsTelemetryServerUrlKey,
            default_value="",
        )

    @telemetry_server_url.setter
    def telemetry_server_url(self, server_url):
        self.telemetry.set_option(
            CONSTS.ConfigsTelemetryServerUrlKey,
            value=server_url
        )

    @property
    def telemetry_include_hooks(self):
        """Whether to include hooks in telemetry."""
        return self.telemetry.get_option(
            CONSTS.ConfigsTelemetryIncludeHooksKey,
            default_value=CONSTS.ConfigsTelemetryIncludeHooksDefault,
        )

    @telemetry_include_hooks.setter
    def telemetry_include_hooks(self, state):
        self.telemetry.set_option(
            CONSTS.ConfigsTelemetryIncludeHooksKey,
            value=state
        )

    @property
    def apptelemetry_status(self):
        """Telemetry status."""
        return self.telemetry.get_option(
            CONSTS.ConfigsAppTelemetryStatusKey,
            default_value=CONSTS.ConfigsAppTelemetryStatusDefault,
        )

    @apptelemetry_status.setter
    def apptelemetry_status(self, state):
        self.telemetry.set_option(
            CONSTS.ConfigsAppTelemetryStatusKey,
            value=state
        )

    @property
    def apptelemetry_server_url(self):
        """App telemetry server URL."""
        return self.telemetry.get_option(
            CONSTS.ConfigsAppTelemetryServerUrlKey,
            default_value="",
        )

    @apptelemetry_server_url.setter
    def apptelemetry_server_url(self, server_url):
        self.telemetry.set_option(
            CONSTS.ConfigsAppTelemetryServerUrlKey,
            value=server_url
        )

    @property
    def apptelemetry_event_flags(self):
        """Telemetry event flags."""
        return self.telemetry.get_option(
            CONSTS.ConfigsAppTelemetryEventFlagsKey,
            default_value="",
        )

    @apptelemetry_event_flags.setter
    def apptelemetry_event_flags(self, flags):
        self.telemetry.set_option(
            CONSTS.ConfigsAppTelemetryEventFlagsKey,
            value=flags
        )

    @property
    def user_can_update(self):
        """Whether the user can update pyRevit repos."""
        return self.core.get_option(
            CONSTS.ConfigsUserCanUpdateKey,
            default_value=CONSTS.ConfigsUserCanUpdateDefault,
        )

    @user_can_update.setter
    def user_can_update(self, state):
        self.core.set_option(
            CONSTS.ConfigsUserCanUpdateKey,
            value=state
        )

    @property
    def user_can_extend(self):
        """Whether the user can manage pyRevit Extensions."""
        return self.core.get_option(
            CONSTS.ConfigsUserCanExtendKey,
            default_value=CONSTS.ConfigsUserCanExtendDefault,
        )

    @user_can_extend.setter
    def user_can_extend(self, state):
        self.core.set_option(
            CONSTS.ConfigsUserCanExtendKey,
            value=state
        )

    @property
    def user_can_config(self):
        """Whether the user can access the configuration."""
        return self.core.get_option(
            CONSTS.ConfigsUserCanConfigKey,
            default_value=CONSTS.ConfigsUserCanConfigDefault,
        )

    @user_can_config.setter
    def user_can_config(self, state):
        self.core.set_option(
            CONSTS.ConfigsUserCanConfigKey,
            value=state
        )

    @property
    def colorize_docs(self):
        """Whether to enable the document colorizer."""
        return self.core.get_option(
            CONSTS.ConfigsColorizeDocsKey,
            default_value=CONSTS.ConfigsColorizeDocsDefault,
        )

    @colorize_docs.setter
    def colorize_docs(self, state):
        self.core.set_option(
            CONSTS.ConfigsColorizeDocsKey,
            value=state
        )

    @property
    def tooltip_debug_info(self):
        """Whether to append debug info on tooltips."""
        return self.core.get_option(
            CONSTS.ConfigsAppendTooltipExKey,
            default_value=CONSTS.ConfigsAppendTooltipExDefault,
        )

    @tooltip_debug_info.setter
    def tooltip_debug_info(self, state):
        self.core.set_option(
            CONSTS.ConfigsAppendTooltipExKey,
            value=state
        )

    @property
    def routes_server(self):
        """Whether the server routes are enabled."""
        return self.routes.get_option(
            CONSTS.ConfigsRoutesServerKey,
            default_value=CONSTS.ConfigsRoutesServerDefault,
        )

    @routes_server.setter
    def routes_server(self, state):
        self.routes.set_option(
            CONSTS.ConfigsRoutesServerKey,
            value=state
        )

    @property
    def respect_language_direction(self):
        """Whether the system respects the language direction."""
        return False

    @respect_language_direction.setter
    def respect_language_direction(self, state):
        pass

    def get_config_version(self):
        """Return version of config file used for change detection.

        Returns:
            (str): hash of the config file
        """
        return self.get_config_file_hash()

    def get_thirdparty_ext_root_dirs(self, include_default=True):
        """Return a list of external extension directories set by the user.

        Returns:
            (list[str]): External user extension directories.
        """
        dir_list = set()
        if include_default:
            # add default ext path
            dir_list.add(THIRDPARTY_EXTENSIONS_DEFAULT_DIR)
        try:
            dir_list.update([
                op.expandvars(op.normpath(x))
                for x in self.core.get_option(
                    CONSTS.ConfigsUserExtensionsKey,
                    default_value=[]
                )])
        except Exception as read_err:
            mlogger.error('Error reading list of user extension folders. | %s',
                          read_err)

        return [x for x in dir_list if op.exists(x)]

    def get_ext_root_dirs(self):
        """Return a list of all extension directories.

        Returns:
            (list[str]): user extension directories.

        """
        dir_list = set()
        if op.exists(EXTENSIONS_DEFAULT_DIR):
            dir_list.add(EXTENSIONS_DEFAULT_DIR)
        dir_list.update(self.get_thirdparty_ext_root_dirs())
        return list(dir_list)

    def get_ext_sources(self):
        """Return a list of extension definition source files."""
        ext_sources = self.environment.get_option(
            CONSTS.EnvConfigsExtensionLookupSourcesKey,
            default_value=[],
        )
        return list(set(ext_sources))

    def set_thirdparty_ext_root_dirs(self, path_list):
        """Updates list of external extension directories in config file.

        Args:
            path_list (list[str]): list of external extension paths
        """
        for ext_path in path_list:
            if not op.exists(ext_path):
                raise PyRevitException("Path \"%s\" does not exist." % ext_path)

        try:
            self.core.userextensions = \
                [op.normpath(x) for x in path_list]
        except Exception as write_err:
            mlogger.error('Error setting list of user extension folders. | %s',
                          write_err)

    def get_current_attachment(self):
        """Return current pyRevit attachment."""
        try:
            return PyRevit.PyRevitAttachments.GetAttached(int(HOST_APP.version))
        except PyRevitException as ex:
            mlogger.error('Error getting current attachment. | %s', ex)

    def get_active_cpython_engine(self):
        """Return active cpython engine."""
        # try to find attachment and get engines from the clone
        attachment = self.get_current_attachment()
        if attachment and attachment.Clone:
            clone = attachment.Clone
        else:
            # if can not find attachment, instantiate a temp clone
            try:
                clone = PyRevit.PyRevitClone(clonePath=HOME_DIR)
            except Exception as cEx:
                mlogger.debug('Can not create clone from path: %s', str(cEx))
                clone = None
        # find cpython engines
        engines = clone.GetCPythonEngines() if clone else []
        cpy_engines_dict = {x.Version: x for x in engines}
        mlogger.debug('cpython engines dict: %s', cpy_engines_dict)

        if not cpy_engines_dict:
            mlogger.error(
                'Can not determine cpython engines for current attachment: %s',
                attachment
            )
            return None
        # grab cpython engine configured to be used by user
        try:
            cpyengine_ver = int(self.cpython_engine_version)
        except (ValueError, TypeError):
            cpyengine_ver = 000

        try:
            return cpy_engines_dict[cpyengine_ver]
        except KeyError:
            # return the latest cpython engine
            return max(cpy_engines_dict.values(), key=lambda x: x.Version.Version)

    def set_active_cpython_engine(self, pyrevit_engine):
        """Set the active CPython engine.

        Args:
            pyrevit_engine (PyRevitEngine): python engine to set as active
        """
        self.cpython_engine_version = pyrevit_engine.Version

    @property
    def is_readonly(self):
        """bool: whether the config is read only."""
        return self._admin

    def save_changes(self):
        """Save user config into associated config file."""
        if not self._admin and self.config_file:
            try:
                super(PyRevitConfig, self).save()
            except Exception as save_err:
                mlogger.error('Can not save user config to: %s | %s',
                              self.config_file, save_err)

            # adjust environment per user configurations
            self._update_env()
        else:
            mlogger.debug('Config is in admin mode. Skipping save.')

    @staticmethod
    def get_list_separator():
        """Get list separator defined in user os regional settings."""
        intkey = coreutils.get_reg_key(wr.HKEY_CURRENT_USER,
                                       r'Control Panel\International')
        if intkey:
            try:
                return wr.QueryValueEx(intkey, 'sList')[0]
            except Exception:
                return DEFAULT_CSV_SEPARATOR


def find_config_file(target_path):
    """Find config file in target path."""
    return PyRevit.PyRevitConsts.FindConfigFileInDirectory(target_path)


def verify_configs(config_file_path=None):
    """Create a user settings file.

    if config_file_path is not provided, configs will be in memory only

    Args:
        config_file_path (str, optional): config file full name and path

    Returns:
        (pyrevit.userconfig.PyRevitConfig): pyRevit config file handler
    """
    if config_file_path:
        mlogger.debug('Creating default config file at: %s', config_file_path)
        coreutils.touch(config_file_path)

    try:
        parser = PyRevitConfig(cfg_file_path=config_file_path)
    except Exception as read_err:
        # can not create default user config file under appdata folder
        mlogger.warning('Can not create config file under: %s | %s',
                        config_file_path, read_err)
        parser = PyRevitConfig()

    return parser


LOCAL_CONFIG_FILE = ADMIN_CONFIG_FILE = USER_CONFIG_FILE = CONFIG_FILE = ''
user_config = None

# location for default pyRevit config files
LOCAL_CONFIG_FILE = find_config_file(HOME_DIR)
ADMIN_CONFIG_FILE = find_config_file(PYREVIT_ALLUSER_APP_DIR)
USER_CONFIG_FILE = find_config_file(PYREVIT_APP_DIR)

# decide which config file to use
# check if a config file is inside the repo. for developers config override
if LOCAL_CONFIG_FILE:
    CONFIG_TYPE = 'Local'
    CONFIG_FILE = LOCAL_CONFIG_FILE

# check to see if there is any config file provided by admin
elif ADMIN_CONFIG_FILE \
        and os.access(ADMIN_CONFIG_FILE, os.W_OK) \
        and not USER_CONFIG_FILE:
    # if yes, copy that and use as default
    # if admin config file is writable it means it is provided
    # to bootstrap the first pyRevit run
    try:
        CONFIG_TYPE = 'Seed'
        # make a local copy if one does not exist
        PyRevit.PyRevitConfigs.SetupConfig(ADMIN_CONFIG_FILE)
        CONFIG_FILE = find_config_file(PYREVIT_APP_DIR)
    except Exception as adminEx:
        # if init operation failed, make a new config file
        CONFIG_TYPE = 'New'
        # setup config file name and path
        CONFIG_FILE = appdata.get_universal_data_file(file_id='config',
                                                        file_ext='ini')
        mlogger.warning(
            'Failed to initialize config from seed file at %s\n'
            'Using default config file',
            ADMIN_CONFIG_FILE
        )

# unless it's locked. then read that config file and set admin-mode
elif ADMIN_CONFIG_FILE \
        and not os.access(ADMIN_CONFIG_FILE, os.W_OK):
    CONFIG_TYPE = 'Admin'
    CONFIG_FILE = ADMIN_CONFIG_FILE

# if a config file is available for user use that
elif USER_CONFIG_FILE:
    CONFIG_TYPE = 'User'
    CONFIG_FILE = USER_CONFIG_FILE

# if nothing can be found, make a new one
else:
    CONFIG_TYPE = 'New'
    # setup config file name and path
    CONFIG_FILE = appdata.get_universal_data_file(file_id='config',
                                                    file_ext='ini')

mlogger.debug('Using %s config file: %s', CONFIG_TYPE, CONFIG_FILE)

# read config, or setup default config file if not available
# this pushes reading settings at first import of this module.
try:
    verify_configs(CONFIG_FILE)
    user_config = PyRevitConfig(cfg_file_path=CONFIG_FILE,
                                config_type=CONFIG_TYPE)
    upgrade.upgrade_user_config(user_config)
    user_config.save_changes()
except Exception as cfg_err:
    mlogger.debug('Can not read confing file at: %s | %s',
                    CONFIG_FILE, cfg_err)
    mlogger.debug('Using configs in memory...')
    user_config = verify_configs()
