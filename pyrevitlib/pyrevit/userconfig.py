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
configuration by pyRevit scripts through `pyrevit.script.get_config`.

Examples:
    ```python
    from pyrevit import script
    cfg = script.get_config()
    cfg.property = value
    cfg.get_option('property', default_value)
    script.save_config()
    ```


Typed section access is the preferred way to reach the built-in settings.
The `core`, `routes`, and `telemetry` properties expose the strongly-typed
sections backed by the shared configuration service, so a setting can be read
or written by its section and name directly:

Examples:
    ```python
    user_config.core.RocketMode = True
    value = user_config.core.RocketMode
    ```

The flat snake_case accessors (e.g. `user_config.rocket_mode`) are convenience
aliases over these sections and are considered legacy: prefer the typed
`section.name` form in new code. The aliases are expected to be deprecated in a
future release once callers have migrated, so avoid adding new ones.
"""
#pylint: disable=C0103,C0413,W0703
import json
import os.path as op

from pyrevit import EXEC_PARAMS, HOME_DIR, HOST_APP
from pyrevit import PyRevitException
from pyrevit import EXTENSIONS_DEFAULT_DIR, THIRDPARTY_EXTENSIONS_DEFAULT_DIR
from pyrevit import framework
from pyrevit.compat import winreg as wr
from pyrevit.coreutils.configparser import ConfigSections

from pyrevit.labs import PyRevit
from pyrevit.labs import Common
from pyrevit.labs import ConfigurationService

from pyrevit import coreutils
from pyrevit.coreutils import logger


DEFAULT_CSV_SEPARATOR = ','


mlogger = logger.get_logger(__name__)


# Re-exported for extensions that do `from pyrevit.userconfig import CONSTS`.
CONSTS = PyRevit.PyRevitConsts


class _SectionCompatWrapper(object):
    """Read/write access to a typed C# section (Core/Routes/Telemetry).

    Reads come from the section snapshot. Writes are persisted through the
    shared configuration service so an edit lands in the backing store
    immediately, rather than mutating the snapshot: the service rebuilds those
    snapshots on any store change, so a snapshot-only edit is silently dropped
    the moment an unrelated write (another section, the multi-section save
    itself) advances the store.

    Also exposes .get_option()/.set_option() for extensions.
    """
    _INTERNAL_ATTRS = (
        '_section_name', '_csharp', '_config',
        '_config_service', '_config_name',
    )

    def __init__(self, section_name, csharp_section, configuration,
                 config_service, config_name):
        self._section_name = section_name
        self._csharp = csharp_section
        self._config = configuration
        self._config_service = config_service
        self._config_name = config_name

    def get_option(self, op_name, default_value=None):
        value = self._config.GetRawValueOrDefault(self._section_name, op_name, None)
        if value is None:
            return default_value
        try:
            return json.loads(value)
        except (ValueError, TypeError):
            try:
                return json.loads(value.replace("'", '"'))
            except (ValueError, TypeError):
                return value

    def set_option(self, op_name, value):
        self._config.SetRawValue(
            self._section_name, op_name,
            json.dumps(value, separators=(',', ':'), ensure_ascii=False)
        )

    def remove_option(self, option_name):
        return self._config.RemoveOption(self._section_name, option_name)

    def has_option(self, option_name):
        """Check if this section contains the given option.

        Args:
            option_name (str): name of the option

        Returns:
            (bool): whether the option exists
        """
        return self._config.HasSectionKey(self._section_name, option_name)

    def __getattr__(self, name):
        # Internal attributes are assigned in __init__ and resolve without
        # __getattr__; reaching here for one means the object is half-built, and
        # consulting the config would recurse.
        if name.startswith('_'):
            raise AttributeError(name)

        try:
            return getattr(self._csharp, name)
        except AttributeError:
            pass

        # A name the typed section does not declare is looked up as a raw
        # option, so a key this schema does not model is still reachable.
        if self.has_option(name):
            return self.get_option(name)

        raise AttributeError(
            'Parameter does not exist in config file: {}'.format(name))

    def __setattr__(self, name, value):
        if name in self._INTERNAL_ATTRS:
            object.__setattr__(self, name, value)
            return

        if self._csharp.GetType().GetProperty(name) is not None:
            # A typed section property is written through to the shared store;
            # save_changes flushes it to disk once at the end.
            if value is not None:
                pending = type(self._csharp)()
                setattr(pending, name, value)
                self._config_service.ApplySection(self._config_name, pending)
            else:
                setattr(self._csharp, name, value)
        else:
            # Mirrors __getattr__: a name outside the typed schema is stored as
            # a raw option rather than rejected.
            self.set_option(name, value)


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
        # Hand the container an accessor rather than the service itself, so
        # sections already handed to scripts follow a reload instead of holding
        # a replaced service whose edits are never flushed.
        self.config_sections = ConfigSections(self._current_config_service)

        self._update_env()

        self._admin = self.config_service.ReadOnly
        self.config_type = "Admin" if self.config_service.ReadOnly else "User"

    def _current_config_service(self):
        return self.config_service

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
        """Path of the config file backing this configuration.

        This is the file the service resolved on load, which may be a
        read-only all-users config.
        """
        resolved = self._get_default_config().ConfigurationPath
        return resolved or PyRevit.PyRevitConsts.ConfigFilePath

    @property
    def environment(self):
        """Environment section."""
        return self.config_service.Environment

    def _get_default_config(self):
        return self.config_service[ConfigurationService.DefaultConfigurationName]

    @property
    def core(self):
        """Core section (supports .get_option/.set_option for extension compat)."""
        return _SectionCompatWrapper(
            "core", self.config_service.Core, self._get_default_config(),
            self.config_service, ConfigurationService.DefaultConfigurationName
        )

    @property
    def routes(self):
        """Routes section (supports .get_option/.set_option for extension compat)."""
        return _SectionCompatWrapper(
            "routes", self.config_service.Routes, self._get_default_config(),
            self.config_service, ConfigurationService.DefaultConfigurationName
        )

    @property
    def telemetry(self):
        """Telemetry section (supports .get_option/.set_option for extension compat)."""
        return _SectionCompatWrapper(
            "telemetry", self.config_service.Telemetry, self._get_default_config(),
            self.config_service, ConfigurationService.DefaultConfigurationName
        )

    @property
    def bin_cache(self):
        """Whether to use the cache for extensions."""
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
        return PyRevit.PyRevitConfigs.ToLoggingLevel(
            self.core.Debug, self.core.Verbose)

    @log_level.setter
    def log_level(self, state):
        self.core.Debug = PyRevit.PyRevitConfigs.LoggingLevelDebugFlag(state)
        self.core.Verbose = PyRevit.PyRevitConfigs.LoggingLevelVerboseFlag(state)

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
    def new_loader(self):
        """Whether to use new csharp loader."""
        return self.core.NewLoader

    @new_loader.setter
    def new_loader(self, state):
        self.core.NewLoader = state

    @property
    def read_script_metadata(self):
        """Whether to read script metadata (__title__, __author__, etc) from Python scripts.

        When False, pyRevit will skip reading metadata from .py script files and will
        only use values from bundle.yaml. This improves startup performance but may
        affect commands that rely on script-level metadata.
        """
        return self.core.ReadScriptMetadata

    @read_script_metadata.setter
    def read_script_metadata(self, state):
        self.core.ReadScriptMetadata = state

    @property
    def output_close_others(self):
        """Whether to close other output windows."""
        return self.core.CloseOtherOutputs

    @output_close_others.setter
    def output_close_others(self, state):
        self.core.CloseOtherOutputs = state

    @property
    def output_close_mode_enum(self):
        """Output window closing mode as enum (CurrentCommand | CloseAll)."""
        return PyRevit.PyRevitConfigs.ToCloseOutputMode(self.core.CloseOutputMode)

    @output_close_mode_enum.setter
    def output_close_mode_enum(self, mode):
        self.core.CloseOutputMode = \
            PyRevit.PyRevitConfigs.CloseOutputModeConfigValue(mode)

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
        if stylesheet_filepath:
            self.core.OutputStyleSheet = stylesheet_filepath
        else:
            # A null property is left untouched on save, so remove the key
            # explicitly to actually clear a previously stored stylesheet.
            self.core.OutputStyleSheet = None
            self.core.remove_option("outputstylesheet")

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
        """App telemetry status."""
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
        """App telemetry event flags."""
        return self.telemetry.AppTelemetryEventFlags

    @apptelemetry_event_flags.setter
    def apptelemetry_event_flags(self, flags):
        self.telemetry.AppTelemetryEventFlags = flags

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

    def get_thirdparty_ext_root_dirs(self, include_default=True):
        """Return a list of external extension directories set by the user.

        Returns:
            (list[str]): External user extension directories.
        """
        # Deterministic ordering: default path first, then config-file order,
        # with duplicate paths removed. User paths are resolved by the shared C#
        # core so the loader and CLI agree on normalization and existence.
        seen = set()
        dir_list = []
        if include_default:
            norm = op.normpath(THIRDPARTY_EXTENSIONS_DEFAULT_DIR)
            if norm not in seen:
                seen.add(norm)
                dir_list.append(norm)
        try:
            for x in PyRevit.PyRevitExtensions.ResolveUserExtensionPaths():
                if x not in seen:
                    seen.add(x)
                    dir_list.append(x)
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
            self.core.UserExtensions = framework.List[str](
                [op.normpath(x) for x in path_list]
            )
        except Exception as write_err:
            mlogger.error('Error setting list of user extension folders. | %s',
                          write_err)

    def get_current_attachment(self, cached=True):
        """Return current pyRevit attachment.

        The shared C# attachment cache lets all script engines reuse a single
        disk lookup. Cleared on reload and on Attach/Detach/clone changes.

        Args:
            cached (bool): set False to bypass the session cache when the
                attachment may have changed out of process.
        """
        try:
            host_version = int(HOST_APP.version)
            if cached:
                return PyRevit.PyRevitAttachments.GetAttachedCached(host_version)
            return PyRevit.PyRevitAttachments.GetAttached(host_version)
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
        """Save user config into associated config file.

        A failed write is logged rather than raised: settings are not worth
        aborting a session load or a settings dialog over.
        """
        if not self._admin:
            # Typed and dynamic section edits have already been written through
            # to the in-memory store; flush the whole default config to disk once.
            try:
                self.config_service[
                    ConfigurationService.DefaultConfigurationName
                ].SaveConfiguration()
            except Exception as save_err:
                # Report the resolved path directly; the config_file property
                # falls back to a path helper that creates files on disk, which
                # must not run from an error handler.
                mlogger.error(
                    'Can not save user config to: %s | %s',
                    self._get_default_config().ConfigurationPath, save_err)

            # adjust environment per user configurations
            self._update_env()
        else:
            mlogger.debug('Config is in admin mode. Skipping save.')

    def reload(self):
        """Reload configuration from disk, discarding unsaved in-memory edits."""
        # Drop the cached shared service so the next access re-reads from disk
        # across every consumer, not just this object.
        PyRevit.PyRevitConfigs.ReloadConfig()
        self.config_service = PyRevit.PyRevitConfigs.GetConfigFile()

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
        """Check if the config contains the given section.

        Args:
            section_name (str): name of the section

        Returns:
            (bool): whether the section exists
        """
        return self.config_sections.has_section(section_name)

    def add_section(self, section_name):
        """Add a new section to the config.

        Args:
            section_name (str): name of the section

        Returns:
            (ConfigSection): the added section
        """
        return self.config_sections.add_section(section_name)

    def get_section(self, section_name):
        """Get the named config section.

        Args:
            section_name (str): name of the section

        Returns:
            (ConfigSection): the requested section

        Raises:
            AttributeError: if the section does not exist
        """
        return self.config_sections.get_section(section_name)

    def remove_section(self, section_name):
        """Remove the named section from the config.

        Args:
            section_name (str): name of the section
        """
        self.config_sections.remove_section(section_name)


user_config = None

# Pin install-scope detection to the running clone so the config store resolves
# the same scope the loader was launched from (rather than the executing
# assembly's location).
try:
    Common.PyRevitInstallScope.SetRuntimeInstallRoot(HOME_DIR)
except Exception as install_root_ex:
    mlogger.debug('Could not set runtime install root: %s', install_root_ex)

# Skipped in doc mode, where no configuration backend is available.
if not getattr(EXEC_PARAMS, 'doc_mode', False):
    user_config = PyRevitConfig(PyRevit.PyRevitConfigs.GetConfigFile())
