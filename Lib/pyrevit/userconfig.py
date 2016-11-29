import os.path as op

from pyrevit import FORCED_DEBUG_MODE_PARAM, USER_ROAMING_DIR, PYREVIT_ASSEMBLY_NAME
from pyrevit.core.exceptions import PyRevitException
from pyrevit.core.logger import get_logger
from pyrevit.coreutils import verify_directory
from pyrevit.coreutils.cfgparser import PyRevitConfigParser

# noinspection PyUnresolvedReferences
from System.IO import IOException


logger = get_logger(__name__)


# default directory for user config file

SETTINGS_FILE_EXTENSION = '.ini'
USER_DEFAULT_SETTINGS_FILENAME = 'config' + SETTINGS_FILE_EXTENSION

USER_SETTINGS_DIR = op.join(USER_ROAMING_DIR, PYREVIT_ASSEMBLY_NAME)
CONFIG_FILE_PATH = op.join(USER_SETTINGS_DIR, USER_DEFAULT_SETTINGS_FILENAME)
logger.debug('User config file: {}'.format(CONFIG_FILE_PATH))


INIT_SETTINGS_SECTION_NAME = 'init'


def _get_default_config_parser():
    """Creates a user settings file under USER_SETTINGS_DIR with default hard-coded values."""
    try:
        # make sure folder exists or can be created if not
        verify_directory(USER_SETTINGS_DIR)
        user_cfg_parser = PyRevitConfigParser(CONFIG_FILE_PATH)
    except (OSError, IOException) as err:
        # can not create default user config file under USER_SETTINGS_DIR
        logger.error('Can not create config file folder under: {}'.format(USER_SETTINGS_DIR, err))
        user_cfg_parser = PyRevitConfigParser()

    user_cfg_parser.add_section(INIT_SETTINGS_SECTION_NAME)
    user_cfg_parser.init.verbose = False
    user_cfg_parser.init.debug = False


def _load_config():
    """Loads settings from settings file."""
    # try opening and reading config file in order.
    try:
        user_cfg_parser = PyRevitConfigParser(CONFIG_FILE_PATH)
        # set log mode on the logger module based on user settings (overriding the defaults)
        if not FORCED_DEBUG_MODE_PARAM:
            if user_cfg_parser.init.debug:
                logger.set_debug_mode()
            elif user_cfg_parser.init.verbose:
                logger.set_verbose_mode()

        return user_cfg_parser

    except PyRevitException as load_err:
        logger.debug('Error loading eisting config file. | {}'.format(load_err))
        return _get_default_config_parser()


# this pushes reading settings at first import of this module.
user_config = _load_config()
