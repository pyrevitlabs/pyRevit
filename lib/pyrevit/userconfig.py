from pyrevit import EXEC_PARAMS, EXTENSIONS_DEFAULT_DIR
from pyrevit.coreutils import touch
import pyrevit.coreutils.appdata as appdata
from pyrevit.coreutils.configparser import PyRevitConfigParser
from pyrevit.coreutils.logger import get_logger, set_file_logging

# noinspection PyUnresolvedReferences
from System.IO import IOException


logger = get_logger(__name__)


# default directory for user config file
SETTINGS_FILE_EXTENSION = 'ini'
USER_DEFAULT_SETTINGS_FILE_ID = 'config'
CONFIG_FILE_PATH = appdata.get_universal_data_file(file_id=USER_DEFAULT_SETTINGS_FILE_ID,
                                                   file_ext=SETTINGS_FILE_EXTENSION)
logger.debug('User config file: {}'.format(CONFIG_FILE_PATH))


INIT_SETTINGS_SECTION = 'init'
COMMAND_ALIAS_SECTION = 'alias'


class PyRevitConfig(PyRevitConfigParser):
    def __init__(self, cfg_file_path=None):
        """Loads settings from settings file."""
        self.config_file = cfg_file_path
        # try opening and reading config file in order.
        PyRevitConfigParser.__init__(self, cfg_file_path=cfg_file_path)
        # set log mode on the logger module based on user settings (overriding the defaults)
        try:
            if not EXEC_PARAMS.forced_debug_mode:
                if self.init.debug:
                    logger.set_debug_mode()
                    logger.debug('Debug mode is enabled in user settings.')
                elif self.init.verbose:
                    logger.set_verbose_mode()

            set_file_logging(self.init.filelogging)
        except:
            pass

    def get_ext_root_dirs(self):
        dir_list = list()
        dir_list.append(EXTENSIONS_DEFAULT_DIR)
        try:
            dir_list.extend([p for p in self.init.userextensions])
        except Exception as read_err:
            logger.error('Error reading list of user extension folders. | {}'.format(read_err))

        return dir_list

    def get_alias(self, original_name):
        try:
            return self.alias.get_option(original_name)
        except AttributeError:
            return None

    def save_changes(self):
        PyRevitConfigParser.save(self, self.config_file)
        logger.reset_level()
        if not EXEC_PARAMS.forced_debug_mode:
            if self.init.debug:
                logger.set_debug_mode()
            elif self.init.verbose:
                logger.set_verbose_mode()

        # set_file_logging(self.init.filelogging)


def _get_default_config_parser(config_file_path):
    """
    Creates a user settings file under USER_SETTINGS_DIR with default hard-coded values.

    Returns:
        PyRevitConfig:
    """

    logger.debug('Creating default config file at: {} '.format(CONFIG_FILE_PATH))
    touch(config_file_path)

    try:
        parser = PyRevitConfig(cfg_file_path=config_file_path)
    except Exception as read_err:
        # can not create default user config file under USER_SETTINGS_DIR
        logger.error('Can not create config file under: {} | {}'.format(config_file_path, read_err))
        parser = PyRevitConfig()

    parser.add_section(INIT_SETTINGS_SECTION)
    parser.add_section(COMMAND_ALIAS_SECTION)
    parser.init.checkupdates = False
    parser.init.verbose = True
    parser.init.debug = False
    parser.init.filelogging = False
    parser.init.userextensions = '[]'
    parser.init.compilecsharp = True
    parser.init.compilevb = True

    parser.save(cfg_file_path=config_file_path)
    logger.debug('Default config saved to: {}'.format(config_file_path))
    return parser


# this pushes reading settings at first import of this module.
try:
    user_config = PyRevitConfig(cfg_file_path=CONFIG_FILE_PATH)
except Exception as cfg_err:
    logger.debug('Can not read existing confing file at: {} | {}'.format(CONFIG_FILE_PATH, cfg_err))
    user_config = _get_default_config_parser(CONFIG_FILE_PATH)
