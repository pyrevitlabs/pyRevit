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
from pyrevit.compat import winreg as wr
from pyrevit.coreutils.configparser import ConfigSections

from pyrevit.labs import PyRevit
from pyrevit.labs import ConfigurationService

from pyrevit import coreutils
from pyrevit.coreutils import logger


DEFAULT_CSV_SEPARATOR = ','


mlogger = logger.get_logger(__name__)


CONSTS = PyRevit.PyRevitConsts


class PyRevitConfig(object):
    """Provide read/write access to pyRevit configuration.

    Args:
        config_service (IConfigurationService): configuration service.

    Examples:
        ```python
        cfg = PyRevitConfig(config_service)
        cfg.add_section('sectionname')
        cfg.sectionname.property = value
        cfg.sectionname.get_option('property', default_value)
        cfg.save_changes()
        ```
    """

    def __init__(self, config_service):
        # set log mode on the logger module based on
        # user settings (overriding the defaults)
        self.config_service = config_service
        self.config_sections = ConfigSections(self.config_service[ConfigurationService.DefaultConfigurationName])

        self._update_env()

        self._admin = self.config_service.ReadOnly
        self.config_type = "Admin" if self.config_service.ReadOnly else "User"

    def _update_env(self):
        # update the debug level based on user config
        mlogger.reset_level()

        try:
            # first check to see if command is not in forced debug mode
            if not EXEC_PARAMS.debug_mode:
                if self.core.Debug:
                    mlogger.set_debug_mode()
                    mlogger.debug('Debug mode is enabled in user settings.')
                elif self.core.Verbose:
                    mlogger.set_verbose_mode()

            logger.set_file_logging(self.core.FileLogging)
        except Exception as env_update_err:
            mlogger.debug('Error updating env variable per user config. | %s',
                          env_update_err)

    @property
    def config_file(self):
        """Current config file path."""
        return PyRevit.PyRevitConsts.ConfigFilePath

    @property
    def environment(self):
        """Environment section."""
        return self.config_service.Environment

    @property
    def core(self):
        """Core section."""
        return self.config_service.Core

    @property
    def routes(self):
        """Routes section."""
        return self.config_service.Routes

    @property
    def telemetry(self):
        """Telemetry section."""
        return self.config_service.Telemetry

    @property
    def bin_cache(self):
        """"Whether to use the cache for extensions."""
        return self.core.BinCache

    @bin_cache.setter
    def bin_cache(self, state):
        self.core.BinCache = state

    @property
    def check_updates(self):
        """Whether to check for updates."""
        return self.core.CheckUpdates

    @check_updates.setter
    def check_updates(self, state):
        self.core.CheckUpdates = state

    @property
    def auto_update(self):
        """Whether to automatically update pyRevit."""
        return self.core.AutoUpdate

    @auto_update.setter
    def auto_update(self, state):
        self.core.AutoUpdate = state

    @property
    def rocket_mode(self):
        """Whether to enable rocket mode."""
        return self.core.RocketMode

    @rocket_mode.setter
    def rocket_mode(self, state):
        self.core.RocketMode = state

    @property
    def log_level(self):
        """Logging level."""
        if self.core.Debug:
            return PyRevit.PyRevitLogLevels.Debug
        elif self.core.Verbose:
            return PyRevit.PyRevitLogLevels.Verbose
        return PyRevit.PyRevitLogLevels.Quiet

    @log_level.setter
    def log_level(self, state):
        if state == PyRevit.PyRevitLogLevels.Debug:
            self.core.Debug = True
            self.core.Verbose = True
        elif state == PyRevit.PyRevitLogLevels.Verbose:
            self.core.Debug = False
            self.core.Verbose = True
        else:
            self.core.Debug = False
            self.core.Verbose = False

    @property
    def file_logging(self):
        """Whether to enable file logging."""
        return self.core.FileLogging

    @file_logging.setter
    def file_logging(self, state):
        self.core.FileLogging = state

    @property
    def startuplog_timeout(self):
        """Timeout for the startup log."""
        return self.core.StartupLogTimeout

    @startuplog_timeout.setter
    def startuplog_timeout(self, timeout):
        self.core.StartupLogTimeout = timeout

    @property
    def required_host_build(self):
        """Host build required to run the commands."""
        return self.core.RequiredHostBuild

    @required_host_build.setter
    def required_host_build(self, buildnumber):
        self.core.RequiredHostBuild = buildnumber

    @property
    def min_host_drivefreespace(self):
        """Minimum free space for running the commands."""
        return self.core.MinHostDriveFreeSpace

    @min_host_drivefreespace.setter
    def min_host_drivefreespace(self, freespace):
        self.core.MinHostDriveFreeSpace = freespace

    @property
    def load_beta(self):
        """Whether to load commands in beta."""
        return self.core.LoadBeta

    @load_beta.setter
    def load_beta(self, state):
        self.core.LoadBeta = state

    @property
    def cpython_engine_version(self):
        """CPython engine version to use."""
        return self.core.CpythonEngineVersion

    @cpython_engine_version.setter
    def cpython_engine_version(self, version):
        self.core.CpythonEngineVersion = int(version)

    @property
    def user_locale(self):
        """User locale."""
        return self.core.UserLocale

    @user_locale.setter
    def user_locale(self, local_code):
        self.core.UserLocale = local_code

    @property
    def output_stylesheet(self):
        """Stylesheet used for output."""
        return self.core.OutputStyleSheet

    @output_stylesheet.setter
    def output_stylesheet(self, stylesheet_filepath):
        self.core.OutputStyleSheet = stylesheet_filepath

    @property
    def routes_host(self):
        """Routes API host."""
        return self.routes.Host

    @routes_host.setter
    def routes_host(self, routes_host):
        self.routes.Host = routes_host

    @property
    def routes_port(self):
        """API routes port."""
        return self.routes.Port

    @routes_port.setter
    def routes_port(self, port):
        self.routes.Port = port

    @property
    def load_core_api(self):
        """Whether to load pyRevit core api."""
        return self.routes.LoadCoreApi

    @load_core_api.setter
    def load_core_api(self, state):
        self.routes.LoadCoreApi = state

    @property
    def telemetry_utc_timestamp(self):
        """Whether to use UTC timestamps in telemetry."""
        return self.telemetry.TelemetryUseUtcTimeStamps

    @telemetry_utc_timestamp.setter
    def telemetry_utc_timestamp(self, state):
        self.telemetry.TelemetryUseUtcTimeStamps = state

    @property
    def telemetry_status(self):
        """Telemetry status."""
        return self.telemetry.TelemetryStatus

    @telemetry_status.setter
    def telemetry_status(self, state):
        self.telemetry.TelemetryStatus = state

    @property
    def telemetry_file_dir(self):
        """Telemetry file directory."""
        return self.telemetry.TelemetryFileDir

    @telemetry_file_dir.setter
    def telemetry_file_dir(self, filepath):
        self.telemetry.TelemetryFileDir = filepath

    @property
    def telemetry_server_url(self):
        """Telemetry server URL."""
        return self.telemetry.TelemetryServerUrl

    @telemetry_server_url.setter
    def telemetry_server_url(self, server_url):
        self.telemetry.TelemetryServerUrl = server_url

    @property
    def telemetry_include_hooks(self):
        """Whether to include hooks in telemetry."""
        return self.telemetry.TelemetryIncludeHooks

    @telemetry_include_hooks.setter
    def telemetry_include_hooks(self, state):
        self.telemetry.TelemetryIncludeHooks = state

    @property
    def apptelemetry_status(self):
        """Telemetry status."""
        return self.telemetry.AppTelemetryStatus

    @apptelemetry_status.setter
    def apptelemetry_status(self, state):
        self.telemetry.AppTelemetryStatus = state

    @property
    def apptelemetry_server_url(self):
        """App telemetry server URL."""
        return self.telemetry.AppTelemetryServerUrl

    @apptelemetry_server_url.setter
    def apptelemetry_server_url(self, server_url):
        self.telemetry.AppTelemetryServerUrl = server_url

    @property
    def apptelemetry_event_flags(self):
        """Telemetry event flags."""
        return str(hex(self.telemetry.AppTelemetryEventFlags))

    @apptelemetry_event_flags.setter
    def apptelemetry_event_flags(self, flags):
        self.telemetry.AppTelemetryEventFlags = int(flags, 16)

    @property
    def user_can_update(self):
        """Whether the user can update pyRevit repos."""
        return self.core.UserCanUpdate

    @user_can_update.setter
    def user_can_update(self, state):
        self.core.UserCanUpdate = state

    @property
    def user_can_extend(self):
        """Whether the user can manage pyRevit Extensions."""
        return self.core.UserCanExtend

    @user_can_extend.setter
    def user_can_extend(self, state):
        self.core.UserCanExtend = state

    @property
    def user_can_config(self):
        """Whether the user can access the configuration."""
        return self.core.UserCanConfig

    @user_can_config.setter
    def user_can_config(self, state):
        self.core.UserCanConfig = state

    @property
    def colorize_docs(self):
        """Whether to enable the document colorizer."""
        return self.core.ColorizeDocs

    @colorize_docs.setter
    def colorize_docs(self, state):
        self.core.ColorizeDocs = state

    @property
    def tooltip_debug_info(self):
        """Whether to append debug info on tooltips."""
        return self.core.TooltipDebugInfo

    @tooltip_debug_info.setter
    def tooltip_debug_info(self, state):
        self.core.TooltipDebugInfo = state

    @property
    def routes_server(self):
        """Whether the server routes are enabled."""
        return self.routes.Status

    @routes_server.setter
    def routes_server(self, state):
        self.routes.Status = state

    @property
    def respect_language_direction(self):
        """Whether the system respects the language direction."""
        return False

    @respect_language_direction.setter
    def respect_language_direction(self, state):
        pass

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
        return list(set(self.environment.Sources))

    def set_thirdparty_ext_root_dirs(self, path_list):
        """Updates list of external extension directories in config file.

        Args:
            path_list (list[str]): list of external extension paths
        """
        for ext_path in path_list:
            if not op.exists(ext_path):
                raise PyRevitException("Path \"%s\" does not exist." % ext_path)

        try:
            self.core.UserExtensions = \
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
        if not self._admin:
            self.config_service.SaveSection(ConfigurationService.DefaultConfigurationName, self.core)
            self.config_service.SaveSection(ConfigurationService.DefaultConfigurationName, self.routes)
            self.config_service.SaveSection(ConfigurationService.DefaultConfigurationName, self.telemetry)

            # save all sections (need to dynamic section on python)
            self.config_service[ConfigurationService.DefaultConfigurationName].SaveConfiguration()

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

    """Default config section code"""
    def __iter__(self):
        return self.config_sections.__iter__()

    def __getattr__(self, section_name):
        return self.config_sections.__getattr__(section_name)

    def has_section(self, section_name):
        return self.config_sections.has_section(section_name)

    def add_section(self, section_name):
        return self.config_sections.add_section(section_name)

    def get_section(self, section_name):
        return self.config_sections.get_section(section_name)

    def remove_section(self, section_name):
       self.config_sections.remove_section(section_name)


def find_config_file(target_path):
    """Find config file in target path."""
    return PyRevit.PyRevitConsts.FindConfigFileInDirectory(target_path)


user_config = None

# location for default pyRevit config files
if not EXEC_PARAMS.doc_mode:
    user_config = PyRevitConfig(PyRevit.PyRevitConfigs.GetConfigFile())