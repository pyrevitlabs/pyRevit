import os.path as op

from pyrevit import EXEC_PARAMS, EXTENSIONS_DEFAULT_DIR
from pyrevit.core.exceptions import PyRevitIOError
from pyrevit.core.logger import get_logger
from pyrevit.coreutils.appdata import PYREVIT_APP_DIR
from pyrevit.coreutils.configparser import PyRevitConfigParser


# noinspection PyUnresolvedReferences
from System.IO import IOException


logger = get_logger(__name__)


# default directory for user config file


SETTINGS_FILE_EXTENSION = '.ini'
USER_DEFAULT_SETTINGS_FILENAME = 'config' + SETTINGS_FILE_EXTENSION
CONFIG_FILE_PATH = op.join(PYREVIT_APP_DIR, USER_DEFAULT_SETTINGS_FILENAME)
logger.debug('User config file: {}'.format(CONFIG_FILE_PATH))


INIT_SETTINGS_SECTION = 'init'


class PyRevitConfig(PyRevitConfigParser):
    def __init__(self, cfg_file_path=None):
        """Loads settings from settings file."""
        self.config_file = cfg_file_path
        # try opening and reading config file in order.
        PyRevitConfigParser.__init__(self, cfg_file_path=cfg_file_path)
        # set log mode on the logger module based on user settings (overriding the defaults)
        if not EXEC_PARAMS.forced_debug_mode:
            if self.init.debug:
                logger.set_debug_mode()
            elif self.init.verbose:
                logger.set_verbose_mode()

    def get_ext_root_dirs(self):
        dir_list = list()
        dir_list.append(EXTENSIONS_DEFAULT_DIR)
        try:
            dir_list.extend([p for p in self.init.userextensions])
        except Exception as read_err:
            logger.error('Error reading list of user extension folders. | {}'.format(read_err))

        return dir_list

    def save_changes(self):
        PyRevitConfigParser.save(self, self.config_file)


def _get_default_config_parser():
    """
    Creates a user settings file under USER_SETTINGS_DIR with default hard-coded values.

    Returns:
        PyRevitConfig:
    """
    try:
        parser = PyRevitConfig(CONFIG_FILE_PATH)
    except (OSError, IOException) as io_err:
        # can not create default user config file under USER_SETTINGS_DIR
        logger.error('Can not create config file folder under: {}'.format(CONFIG_FILE_PATH, io_err))
        parser = PyRevitConfig()

    parser.add_section(INIT_SETTINGS_SECTION)
    parser.init.verbose = False
    parser.init.debug = False
    parser.init.userextensions = '[]'
    return parser


# this pushes reading settings at first import of this module.
try:
    user_config = PyRevitConfig(cfg_file_path=CONFIG_FILE_PATH)
except PyRevitIOError as err:
    logger.debug('Can not read existing confing file at: {} | {}'.format(CONFIG_FILE_PATH, err))
    user_config = _get_default_config_parser()
