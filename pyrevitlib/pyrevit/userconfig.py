"""Handle reading and parsing, writin and saving of all user configurations.

All other modules use this module to query user config.
"""

import os
import os.path as op
import shutil

from pyrevit import EXEC_PARAMS, EXTENSIONS_DEFAULT_DIR, HOME_DIR

from pyrevit.coreutils import touch
import pyrevit.coreutils.appdata as appdata
from pyrevit.coreutils.configparser import PyRevitConfigParser
from pyrevit.coreutils.logger import get_logger, set_file_logging
from pyrevit.versionmgr.upgrade import upgrade_user_config


logger = get_logger(__name__)


INIT_SETTINGS_SECTION = 'core'


# location for default pyRevit config files
if not EXEC_PARAMS.doc_mode:
    LOCAL_CONFIG_FILE = op.join(HOME_DIR, 'pyRevit_config.ini')
    ADMIN_CONFIG_DIR = op.join(os.getenv('programdata'), 'pyRevit')

    if op.exists(LOCAL_CONFIG_FILE):
        logger.debug('Using local config file: {}'.format(LOCAL_CONFIG_FILE))
        CONFIG_FILE_PATH = LOCAL_CONFIG_FILE
    else:
        # setup config file name and path
        CONFIG_FILE_PATH = appdata.get_universal_data_file(file_id='config',
                                                           file_ext='ini')
        logger.debug('User config file: {}'.format(CONFIG_FILE_PATH))
else:
    ADMIN_CONFIG_DIR = CONFIG_FILE_PATH = None


# =============================================================================
# fix obsolete config file naming
# config file (and all appdata files) used to include username in the filename
# this fixes the existing config file with obsolete naming, to new format
# pylama:ignore=E402
from pyrevit import PYREVIT_APP_DIR, PYREVIT_FILE_PREFIX_UNIVERSAL_USER

OBSOLETE_CONFIG_FILENAME = '{}_{}'.format(PYREVIT_FILE_PREFIX_UNIVERSAL_USER,
                                          'config.ini')
OBSOLETE_CONFIG_FILEPATH = op.join(PYREVIT_APP_DIR, OBSOLETE_CONFIG_FILENAME)

if op.exists(OBSOLETE_CONFIG_FILEPATH):
    try:
        os.rename(OBSOLETE_CONFIG_FILEPATH, CONFIG_FILE_PATH)
    except Exception as rename_err:
        logger.error('Failed to update the config file name to new format. '
                     'A new configuration file has been created for you '
                     'under \n{}'
                     '\nYour previous pyRevit configuration file still '
                     'existing under the same folder. Please close Revit, '
                     'open both configuration files and copy and paste '
                     'settings from the old config file to new config file. '
                     'Then you can remove the old config file as pyRevit '
                     'will not be using that anymore. | {}'
                     .format(CONFIG_FILE_PATH, rename_err))
# end fix obsolete config file naming
# =============================================================================


class PyRevitConfig(PyRevitConfigParser):
    """Provide read/write access to pyRevit configuration.

    Args:
        cfg_file_path (str): full path to config file to be used.

    Example:
        >>> cfg = PyRevitConfig(cfg_file_path)
        >>> cfg.add_section('sectionname')
        >>> cfg.sectionname.property = value
        >>> cfg.sectionname.get('property', default_value)
        >>> cfg.save_changes()
    """

    def __init__(self, cfg_file_path=None):
        """Load settings from provided config file and setup parser."""
        self.config_file = cfg_file_path

        # try opening and reading config file in order.
        PyRevitConfigParser.__init__(self, cfg_file_path=cfg_file_path)

        # set log mode on the logger module based on
        # user settings (overriding the defaults)
        self._update_env()

    def _update_env(self):
        # update the debug level based on user config
        logger.reset_level()

        try:
            # first check to see if command is not in forced debug mode
            if not EXEC_PARAMS.forced_debug_mode:
                if self.core.debug:
                    logger.set_debug_mode()
                    logger.debug('Debug mode is enabled in user settings.')
                elif self.core.verbose:
                    logger.set_verbose_mode()

            set_file_logging(self.core.filelogging)
        except Exception as env_update_err:
            logger.debug('Error updating env variable per user config. | {}'
                         .format(env_update_err))

    def get_config_version(self):
        """Return version of config file used for change detection."""
        return self.get_config_file_hash()

    def get_ext_root_dirs(self):
        """Return a list of all extension directories.

        Returns:
            :obj:`list`: list of strings. user extension directories.

        """
        dir_list = list()
        dir_list.append(EXTENSIONS_DEFAULT_DIR)
        dir_list.extend(self.get_thirdparty_ext_root_dirs())
        return dir_list

    def get_thirdparty_ext_root_dirs(self):
        """Return a list of external extension directories set by the user.

        Returns:
            :obj:`list`: list of strings. External user extension directories.
        """
        dir_list = list()
        try:
            dir_list.extend([op.expandvars(p)
                             for p in self.core.userextensions])
        except Exception as read_err:
            logger.error('Error reading list of user extension folders. | {}'
                         .format(read_err))

        return dir_list

    def save_changes(self):
        """Save user config into associated config file."""
        try:
            PyRevitConfigParser.save(self, self.config_file)
        except Exception as save_err:
            logger.error('Can not save user config to: {} | {}'
                         .format(self.config_file, save_err))

        # adjust environment per user configurations
        self._update_env()


def _set_hardcoded_config_values(parser):
    """Set default config values for user configuration.

    Args:
        parser (:obj:`pyrevit.userconfig.PyRevitConfig`):
            parser to accept the default values
    """
    # hard-coded values
    parser.add_section('core')
    parser.core.checkupdates = False
    parser.core.autoupdate = False
    parser.core.verbose = True
    parser.core.debug = False
    parser.core.filelogging = True
    parser.core.startuplogtimeout = 10
    parser.core.userextensions = []
    parser.core.compilecsharp = True
    parser.core.compilevb = True
    parser.core.loadbeta = False
    parser.core.rocketmode = False


def _get_default_config_parser(config_file_path):
    """Create a user settings file.

    Args:
        config_file_path (str): config file full name and path

    Returns:
        :obj:`pyrevit.userconfig.PyRevitConfig`: pyRevit config file handler
    """
    logger.debug('Creating default config file at: {} '
                 .format(CONFIG_FILE_PATH))
    touch(config_file_path)

    try:
        parser = PyRevitConfig(cfg_file_path=config_file_path)
    except Exception as read_err:
        # can not create default user config file under appdata folder
        logger.debug('Can not create config file under: {} | {}'
                     .format(config_file_path, read_err))
        parser = PyRevitConfig()

    # set hard-coded values
    _set_hardcoded_config_values(parser)

    # save config into config file
    parser.save_changes()
    logger.debug('Default config saved to: {}'
                 .format(config_file_path))

    return parser


def _setup_admin_config():
    """Set up the default config file with hardcoded values."""
    if not op.exists(CONFIG_FILE_PATH) \
            and op.isdir(ADMIN_CONFIG_DIR):
        for entry in os.listdir(ADMIN_CONFIG_DIR):
            if entry.endswith('.ini'):
                sourcecfg = op.join(ADMIN_CONFIG_DIR, entry)
                try:
                    shutil.copyfile(sourcecfg, CONFIG_FILE_PATH)
                    logger.debug('Configured from admin file: {}'
                                 .format(sourcecfg))
                except Exception as copy_err:
                    logger.debug('Error copying admin config file: {} | {}'
                                 .format(sourcecfg, copy_err))
                return True


if not EXEC_PARAMS.doc_mode:
    # check to see if there is any config file provided by admin
    # if yes, copy that and use as default
    _setup_admin_config()

    # read user config, or setup default config file if not available
    # this pushes reading settings at first import of this module.
    try:
        user_config = PyRevitConfig(cfg_file_path=CONFIG_FILE_PATH)
        upgrade_user_config(user_config)
    except Exception as cfg_err:
        logger.debug('Can not read existing confing file at: {} | {}'
                     .format(CONFIG_FILE_PATH, cfg_err))
        user_config = _get_default_config_parser(CONFIG_FILE_PATH)
else:
    user_config = None
