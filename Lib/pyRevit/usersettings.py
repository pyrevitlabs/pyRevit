import os.path as op
import logging
import ConfigParser

from .exceptions import *
from .logger import logger
from .config import LOADER_DIR, USER_SETTINGS_DIR, ARCHIVE_LOG_FOLDER_DEFAULT
from .config import USER_DEFAULT_SETTINGS_FILENAME, ADMIN_DEFAULT_SETTINGS_FILENAME, KEY_VALUE_TRUE, KEY_VALUE_FALSE
from .config import INIT_SETTINGS_SECTION_NAME, GLOBAL_SETTINGS_SECTION_NAME
from .config import LOG_SCRIPT_USAGE_KEY, ARCHIVE_LOG_FOLDER_KEY, VERBOSE_KEY
from .utils import assert_folder


class _PyRevitUserSettings:
    def __init__(self):
        self.verbose = False
        self.logScriptUsage = False
        self.archivelogfolder = ARCHIVE_LOG_FOLDER_DEFAULT

        self._load_settings()

    def _load_settings(self):
        """Loads settings from settings file."""
        read_successful = False

        # prepare user config file address
        user_config_file = op.join(USER_SETTINGS_DIR, USER_DEFAULT_SETTINGS_FILENAME)

        # prepare admin config file address
        admin_config_file = op.join(LOADER_DIR, ADMIN_DEFAULT_SETTINGS_FILENAME)

        # try opening and reading config file in order.
        for config_file in [user_config_file, admin_config_file]:
            try:
                with open(config_file, 'r') as udfile:
                    cparser = ConfigParser.ConfigParser()
                    cparser.readfp(udfile)
                    self.logScriptUsage = True if cparser.get(INIT_SETTINGS_SECTION_NAME,
                                                              LOG_SCRIPT_USAGE_KEY).lower() == KEY_VALUE_TRUE else False
                    self.archivelogfolder = cparser.get(INIT_SETTINGS_SECTION_NAME,
                                                        ARCHIVE_LOG_FOLDER_KEY)
                    self.verbose = True if cparser.get(GLOBAL_SETTINGS_SECTION_NAME,
                                                       VERBOSE_KEY).lower() == KEY_VALUE_TRUE else False
                    # set to true and break if read successful.
                    logger.debug("Successfully read configfile: {}".format(config_file))
                    read_successful = True
                    break
            except:
                # todo: too broad exception
                logger.debug("Can not access config file: {}".format(config_file))
                continue

        # if can not read any settings file then create a user config and fill with default
        if not read_successful:
            if assert_folder(USER_SETTINGS_DIR):
                try:
                    with open(user_config_file, 'w') as udfile:
                        cparser = ConfigParser.ConfigParser()
                        cparser.add_section(GLOBAL_SETTINGS_SECTION_NAME)
                        cparser.set(GLOBAL_SETTINGS_SECTION_NAME,
                                    VERBOSE_KEY, KEY_VALUE_TRUE if self.verbose else KEY_VALUE_FALSE)
                        cparser.add_section(INIT_SETTINGS_SECTION_NAME)
                        cparser.set(INIT_SETTINGS_SECTION_NAME,
                                    LOG_SCRIPT_USAGE_KEY, KEY_VALUE_TRUE if self.logScriptUsage else KEY_VALUE_FALSE)
                        cparser.set(INIT_SETTINGS_SECTION_NAME,
                                    ARCHIVE_LOG_FOLDER_KEY, self.archivelogfolder)
                        cparser.write(udfile)
                        logger.debug('Config file saved under with default settings.')
                        logger.debug('Config file saved under: {}'.format(USER_SETTINGS_DIR))
                except:
                    # todo: too broad exception
                    logger.debug('Can not create config file under: {}'.format(USER_SETTINGS_DIR))
                    logger.debug('Skipping saving config file.')
            else:
                logger.debug('Can not create config file folder under: {}'.format(USER_SETTINGS_DIR))
                logger.debug('Skipping saving config file.')
                logger.debug('Continuing with default hard-coded settings.')

user_settings = _PyRevitUserSettings()
