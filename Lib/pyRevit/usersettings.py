import os
import os.path as op
import ConfigParser as settingsParser

from pyRevit.logger import logger
from pyRevit.exceptions import *
from pyRevit.logger import logger
import pyRevit.config as cfg
import pyRevit.utils as prutils

INIT_SETTINGS_SECTION_NAME = 'init'
GLOBAL_SETTINGS_SECTION_NAME = 'global'
LOG_SCRIPT_USAGE_KEY = "logScriptUsage"
ARCHIVE_LOG_FOLDER_KEY = "archivelogfolder"
VERBOSE_KEY = "verbose"
KEY_VALUE_TRUE = "true"
KEY_VALUE_FALSE = "false"

class _pyrevit_user_settings:
    def __init__(self):
        self.logScriptUsage = False
        self.archivelogfolder = False
        
        self.load_settings()

    def load_settings(self):
        """Loads settings from settings file."""
        # find the user config file
        configfile = op.join(cfg.USER_SETTINGS_DIR, cfg.USER_DEFAULT_SETTINGS_FILENAME)
        configfileismaster = False

        # if a config file exits along side the script loader, this would be used instead.
        if op.exists(op.join(cfg.LOADER_DIR, cfg.PYREVIT_INIT_SCRIPT_NAME + ".ini")):
            configfile = op.join(cfg.LOADER_DIR, cfg.PYREVIT_INIT_SCRIPT_NAME + ".ini")
            configfileismaster = True

        # if the config file exists then read values and apply
        if op.exists(configfile):        # read file and reapply settings
            try:
                with open(configfile,'r') as udfile:
                    cparser = settingsParser.ConfigParser()          
                    cparser.readfp(udfile)
                    logScriptUsageConfigValue = cparser.get(INIT_SETTINGS_SECTION_NAME, LOG_SCRIPT_USAGE_KEY)
                    self.logScriptUsage = True if logScriptUsageConfigValue.lower() == KEY_VALUE_TRUE else False
                    self.archivelogfolder = cparser.get(INIT_SETTINGS_SECTION_NAME, ARCHIVE_LOG_FOLDER_KEY)
                    verbose = True if cparser.get(GLOBAL_SETTINGS_SECTION_NAME, VERBOSE_KEY).lower() == KEY_VALUE_TRUE else False
            except:
                logger.error("Can not access existing config file. Skipping saving config file.")
        # else if the config file is not master config then create a user config and fill with default
        elif not configfileismaster:
            if self.assert_config_folder(cfg.USER_SETTINGS_DIR):
                try:
                    with open(configfile,'w') as udfile:
                        cparser = settingsParser.ConfigParser()
                        cparser.add_section(GLOBAL_SETTINGS_SECTION_NAME)
                        cparser.set(GLOBAL_SETTINGS_SECTION_NAME, VERBOSE_KEY, KEY_VALUE_TRUE if verbose else KEY_VALUE_FALSE)
                        cparser.add_section(INIT_SETTINGS_SECTION_NAME)
                        cparser.set(INIT_SETTINGS_SECTION_NAME, LOG_SCRIPT_USAGE_KEY, KEY_VALUE_TRUE if self.logScriptUsage else KEY_VALUE_FALSE)
                        cparser.set(INIT_SETTINGS_SECTION_NAME, ARCHIVE_LOG_FOLDER_KEY, self.archivelogfolder)
                        cparser.write(udfile)
                        logger.debug('Config file saved under with default settings.')
                        logger.debug('Config file saved under: {}'.format(cfg.USER_SETTINGS_DIR))
                except:
                    logger.error('Can not create config file under: {}'.format(cfg.USER_SETTINGS_DIR))
                    logger.error('Skipping saving config file.')
            else:
                logger.error('Can not create config file folder under: {}'.format(cfg.USER_SETTINGS_DIR))
                logger.error('Skipping saving config file.')

    def assert_config_folder(self, folder):
        return prutils.assert_folder(folder)


usersettings = _pyrevit_user_settings()
