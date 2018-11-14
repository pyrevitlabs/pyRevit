"""Handle reading and parsing, writin and saving of all user configurations.

This module handles the reading and writing of the pyRevit configuration files.
It's been used extensively by pyRevit sub-modules. :obj:`user_config` is
set up automatically in the global scope by this module and can be imported
into scripts and other modules to access the default configurations.

All other modules use this module to query user config.

Example:

    >>> from pyrevit.userconfig import user_config
    >>> user_config.add_section('newsection')
    >>> user_config.newsection.property = value
    >>> user_config.newsection.get('property', default_value)
    >>> user_config.save_changes()


The :obj:`user_config` object is also the destination for reading and writing
configuration by pyRevit scripts through :func:`get_config` of
:mod:`pyrevit.script` module. Here is the function source:

.. literalinclude:: ../../pyrevitlib/pyrevit/script.py
    :pyobject: get_config

Example:

    >>> from pyrevit import script
    >>> cfg = script.get_config()
    >>> cfg.property = value
    >>> cfg.get('property', default_value)
    >>> script.save_config()
"""
#pylint: disable=C0103,C0413,W0703
import os
import os.path as op

from pyrevit import EXEC_PARAMS, EXTENSIONS_DEFAULT_DIR, HOME_DIR
from pyrevit import PYREVIT_ALLUSER_APP_DIR, PYREVIT_APP_DIR

from pyrevit.labs import TargetApps

from pyrevit.coreutils import touch
from pyrevit.coreutils import appdata
from pyrevit.coreutils import configparser
from pyrevit.coreutils import logger
from pyrevit.versionmgr import upgrade


mlogger = logger.get_logger(__name__)


# =============================================================================
# fix obsolete config file naming
# config file (and all appdata files) used to include username in the filename
# this fixes the existing config file with obsolete naming, to new format
# from pyrevit import PYREVIT_APP_DIR, PYREVIT_FILE_PREFIX_UNIVERSAL_USER

# OBSOLETE_CONFIG_FILENAME = '{}_{}'.format(PYREVIT_FILE_PREFIX_UNIVERSAL_USER,
#                                           'config.ini')
# OBSOLETE_CONFIG_FILEPATH = op.join(PYREVIT_APP_DIR, OBSOLETE_CONFIG_FILENAME)

# if op.exists(OBSOLETE_CONFIG_FILEPATH):
#     try:
#         os.rename(OBSOLETE_CONFIG_FILEPATH, CONFIG_FILE)
#     except Exception as rename_err:
#         mlogger.error('Failed to update the config file name to new format. '
#                       'A new configuration file has been created for you '
#                       'under \n{}'
#                       '\nYour previous pyRevit configuration file still '
#                       'existing under the same folder. Please close Revit, '
#                       'open both configuration files and copy and paste '
#                       'settings from the old config file to new config file. '
#                       'Then you can remove the old config file as pyRevit '
#                       'will not be using that anymore. | {}'
#                       .format(CONFIG_FILE, rename_err))
# end fix obsolete config file naming
# =============================================================================


class PyRevitConfig(configparser.PyRevitConfigParser):
    """Provide read/write access to pyRevit configuration.

    Args:
        cfg_file_path (str): full path to config file to be used.
        config_type (str): type of config file

    Example:
        >>> cfg = PyRevitConfig(cfg_file_path)
        >>> cfg.add_section('sectionname')
        >>> cfg.sectionname.property = value
        >>> cfg.sectionname.get('property', default_value)
        >>> cfg.save_changes()
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
            if not EXEC_PARAMS.forced_debug_mode:
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

    def get_config_version(self):
        """Return version of config file used for change detection."""
        return self.get_config_file_hash()

    def get_ext_root_dirs(self):
        """Return a list of all extension directories.

        Returns:
            :obj:`list`: list of strings. user extension directories.

        """
        dir_list = []
        dir_list.append(EXTENSIONS_DEFAULT_DIR)
        dir_list.extend(self.get_thirdparty_ext_root_dirs())
        return dir_list

    def get_thirdparty_ext_root_dirs(self):
        """Return a list of external extension directories set by the user.

        Returns:
            :obj:`list`: list of strings. External user extension directories.
        """
        dir_list = []
        try:
            dir_list.extend([op.expandvars(p)
                             for p in self.core.userextensions])
        except Exception as read_err:
            mlogger.error('Error reading list of user extension folders. | %s',
                          read_err)

        return dir_list

    def save_changes(self):
        """Save user config into associated config file."""
        if not self._admin:
            try:
                super(PyRevitConfig, self).save()
            except Exception as save_err:
                mlogger.error('Can not save user config to: %s | %s',
                              self.config_file, save_err)

            # adjust environment per user configurations
            self._update_env()
        else:
            mlogger.debug('Config is in admin mode. Skipping save.')


def find_config_file(target_path):
    """Find config file in target path."""
    return TargetApps.Revit.PyRevit.FindConfigFileInDirectory(target_path)


def verify_configs(config_file_path=None):
    """Create a user settings file.

    if config_file_path is not provided, configs will be in memory only

    Args:
        config_file_path (str, optional): config file full name and path

    Returns:
        :obj:`pyrevit.userconfig.PyRevitConfig`: pyRevit config file handler
    """
    if config_file_path:
        mlogger.debug('Creating default config file at: %s', config_file_path)
        touch(config_file_path)

    try:
        parser = PyRevitConfig(cfg_file_path=config_file_path)
    except Exception as read_err:
        # can not create default user config file under appdata folder
        mlogger.warning('Can not create config file under: %s | %s',
                        config_file_path, read_err)
        parser = PyRevitConfig()

    # set hard-coded values
    consts = TargetApps.Revit.PyRevitConsts
    # core section
    if not parser.has_section(consts.ConfigsCoreSection):
        parser.add_section(consts.ConfigsCoreSection)
    # checkupates
    if not parser.core.has_option(consts.ConfigsCheckUpdatesKey):
        parser.core.set_option(consts.ConfigsCheckUpdatesKey, False)
    # autoupdate
    if not parser.core.has_option(consts.ConfigsAutoUpdateKey):
        parser.core.set_option(consts.ConfigsAutoUpdateKey, False)
    # verbose
    if not parser.core.has_option(consts.ConfigsVerboseKey):
        parser.core.set_option(consts.ConfigsVerboseKey, True)
    # debug
    if not parser.core.has_option(consts.ConfigsDebugKey):
        parser.core.set_option(consts.ConfigsDebugKey, False)
    # filelogging
    if not parser.core.has_option(consts.ConfigsFileLoggingKey):
        parser.core.set_option(consts.ConfigsFileLoggingKey, False)
    # startuplogtimeout
    if not parser.core.has_option(consts.ConfigsStartupLogTimeoutKey):
        parser.core.set_option(consts.ConfigsStartupLogTimeoutKey, 10)
    # userextensions
    if not parser.core.has_option(consts.ConfigsUserExtensionsKey):
        parser.core.set_option(consts.ConfigsUserExtensionsKey, [])
    # compilecsharp
    if not parser.core.has_option(consts.ConfigsCompileCSharpKey):
        parser.core.set_option(consts.ConfigsCompileCSharpKey, True)
    # compilevb
    if not parser.core.has_option(consts.ConfigsCompileVBKey):
        parser.core.set_option(consts.ConfigsCompileVBKey, True)
    # loadbeta
    if not parser.core.has_option(consts.ConfigsLoadBetaKey):
        parser.core.set_option(consts.ConfigsLoadBetaKey, False)
    # rocketmode
    if not parser.core.has_option(consts.ConfigsRocketModeKey):
        parser.core.set_option(consts.ConfigsRocketModeKey, True)
    # bincache
    if not parser.core.has_option(consts.ConfigsBinaryCacheKey):
        parser.core.set_option(consts.ConfigsBinaryCacheKey, True)
    # usercanupdate
    if not parser.core.has_option(consts.ConfigsUserCanUpdateKey):
        parser.core.set_option(consts.ConfigsUserCanUpdateKey, True)
    # usercanextend
    if not parser.core.has_option(consts.ConfigsUserCanExtendKey):
        parser.core.set_option(consts.ConfigsUserCanExtendKey, True)
    # usercanconfig
    if not parser.core.has_option(consts.ConfigsUserCanConfigKey):
        parser.core.set_option(consts.ConfigsUserCanConfigKey, True)

    # usagelogging section
    if not parser.has_section(consts.ConfigsUsageLoggingSection):
        parser.add_section(consts.ConfigsUsageLoggingSection)
    # usagelogging active
    if not parser.usagelogging.has_option(consts.ConfigsUsageLoggingStatusKey):
        parser.usagelogging.set_option(
            consts.ConfigsUsageLoggingStatusKey, False
            )
    # usagelogging file
    if not parser.usagelogging.has_option(consts.ConfigsUsageLogFilePathKey):
        parser.usagelogging.set_option(consts.ConfigsUsageLogFilePathKey, "")
    # usagelogging server
    if not parser.usagelogging.has_option(consts.ConfigsUsageLogServerUrlKey):
        parser.usagelogging.set_option(consts.ConfigsUsageLogServerUrlKey, "")

    # save config into config file
    if config_file_path:
        parser.save_changes()
        mlogger.debug('Default config saved to: %s', config_file_path)

    return parser


LOCAL_CONFIG_FILE = ADMIN_CONFIG_FILE = USER_CONFIG_FILE = CONFIG_FILE = ''
user_config = None

# location for default pyRevit config files
if not EXEC_PARAMS.doc_mode:
    LOCAL_CONFIG_FILE = find_config_file(HOME_DIR)
    ADMIN_CONFIG_FILE = find_config_file(PYREVIT_ALLUSER_APP_DIR)
    USER_CONFIG_FILE = find_config_file(PYREVIT_APP_DIR)

    # decide which config file to use
    # check if a config file is inside the repo. for developers config override
    if LOCAL_CONFIG_FILE:
        CONFIG_TYPE = 'Local'
        CONFIG_FILE = LOCAL_CONFIG_FILE
    # check to see if there is any config file provided by admin
    elif ADMIN_CONFIG_FILE:
        # if yes, copy that and use as default
        if os.access(ADMIN_CONFIG_FILE, os.W_OK):
            CONFIG_TYPE = 'Seed'
            TargetApps.Revit.PyRevit.SeedConfig(False, ADMIN_CONFIG_FILE)
            CONFIG_FILE = find_config_file(PYREVIT_APP_DIR)
        # unless it's locked. then read that config file and set admin-mode
        else:
            CONFIG_TYPE = 'Admin'
            CONFIG_FILE = ADMIN_CONFIG_FILE
    # if a config file is available for user use that
    elif USER_CONFIG_FILE:
        CONFIG_TYPE = 'User'
        CONFIG_FILE = USER_CONFIG_FILE
    # if nothing can be found, make one
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
    except Exception as cfg_err:
        mlogger.debug('Can not read confing file at: %s | %s',
                      CONFIG_FILE, cfg_err)
        mlogger.debug('Using configs in memory...')
        user_config = verify_configs()
