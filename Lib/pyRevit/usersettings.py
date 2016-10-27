""" Module name: usersettings.py
Copyright (c) 2014-2016 Ehsan Iran-Nejad
Python scripts for Autodesk Revit

This file is part of pyRevit repository at https://github.com/eirannejad/pyRevit

pyRevit is a free set of scripts for Autodesk Revit: you can redistribute it and/or modify
it under the terms of the GNU General Public License version 3, as published by
the Free Software Foundation.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

See this link for a copy of the GNU General Public License protecting this package.
https://github.com/eirannejad/pyRevit/blob/master/LICENSE


~~~
Reads and Writes user settings to config file.
Also provides functionality for adding custom settings for scripts
"""

import os.path as op
import ConfigParser

from .exceptions import ConfigFileError
from .logger import logger
from .config import LOADER_DIR, USER_SETTINGS_DIR
from .config import USER_DEFAULT_SETTINGS_FILENAME, ADMIN_DEFAULT_SETTINGS_FILENAME, KEY_VALUE_TRUE, KEY_VALUE_FALSE
from .config import INIT_SETTINGS_SECTION_NAME, GLOBAL_SETTINGS_SECTION_NAME, ALIAS_SECTION_NAME
from .config import LOG_SCRIPT_USAGE_KEY, ARCHIVE_LOG_FOLDER_KEY, VERBOSE_KEY, DEBUG_KEY
from .config import VERBOSE_KEY_DEFAULT, DEBUG_KEY_DEFAULT, LOG_SCRIPT_USAGE_KEY_DEFAULT, ARCHIVE_LOG_FOLDER_KEY_DEFAULT

from .utils import assert_folder


class _CustomUserSettings:
    """_PyRevitUserSettings.load_parameter returns an instance of this class with parameters corresponding to
    previously saved parameters by the calling script. See load_parameter and save_parameter in _PyRevitUserSettings
    Example:
        user_settings.save_parameter(param, value)
        this_script_settings = user_settings.load_parameters()
        print( this_script_settings.custom_param )
    """
    # todo custom user settings?
    pass


class _PyRevitUserSettings:
    """Private class for handling all functions related to user settings.
     This module reads and writes settings using python native ConfigParser.
     Usage:
     from pyRevit.usersettings import user_settings
     print(user_settings.archivelogfolder)
    """

    def __init__(self):
        self.verbose = VERBOSE_KEY_DEFAULT

        self.logScriptUsage = LOG_SCRIPT_USAGE_KEY_DEFAULT
        self.archivelogfolder = ARCHIVE_LOG_FOLDER_KEY_DEFAULT
        self.debug = DEBUG_KEY_DEFAULT
        self.alias_dict = {}

        # prepare user config file address
        self.user_config_file = op.join(USER_SETTINGS_DIR, USER_DEFAULT_SETTINGS_FILENAME)
        logger.debug('User config file: {}'.format(self.user_config_file))

        # prepare admin config file address
        self.admin_config_file = op.join(LOADER_DIR, ADMIN_DEFAULT_SETTINGS_FILENAME)
        logger.debug('Admin config file: {})'.format(self.admin_config_file))

        # This parameters holds the address to the config file that is successfully read (user or admin)
        self.config_file = None

        # try reading user or admin config files
        if not self._load_settings():
            # if failed, create a user config file with default values
            logger.debug('No config file is found.')
            logger.debug('Saving default config file under {}'.format(USER_SETTINGS_DIR))
            try:
                self._create_default_config_file()
            except ConfigFileError as err:
                logger.error(err.message)
                logger.debug('Skipping saving config file.')
                logger.debug('Continuing with default hard-coded settings.')

    def _load_settings(self):
        """Loads settings from settings file."""
        read_successful = False

        # try opening and reading config file in order.
        for config_file in [self.user_config_file, self.admin_config_file]:
            try:
                logger.debug('Try reading config setting from: {}'.format(config_file))
                with open(config_file, 'r') as udfile:
                    cparser = ConfigParser.ConfigParser()
                    cparser.readfp(udfile)
                    self.verbose = True if cparser.get(GLOBAL_SETTINGS_SECTION_NAME,
                                                       VERBOSE_KEY).lower() == KEY_VALUE_TRUE else False
                    self.debug = True if cparser.get(GLOBAL_SETTINGS_SECTION_NAME,
                                                     DEBUG_KEY).lower() == KEY_VALUE_TRUE else False

                    # set log mode on the logger module based on user settings (overriding the defaults)
                    if self.debug:
                        logger.set_debug_mode()
                    elif self.verbose:
                        logger.set_verbose_mode()

                    self.logScriptUsage = True if cparser.get(INIT_SETTINGS_SECTION_NAME,
                                                              LOG_SCRIPT_USAGE_KEY).lower() == KEY_VALUE_TRUE else False
                    self.archivelogfolder = cparser.get(INIT_SETTINGS_SECTION_NAME,
                                                        ARCHIVE_LOG_FOLDER_KEY)

                    # read command name alias section
                    alias_options = cparser.options(ALIAS_SECTION_NAME)
                    logger.debug('Alias is available for these names: {}'.format(alias_options))
                    for cmd_name in alias_options:
                        cmd_alias_name = cparser.get(ALIAS_SECTION_NAME, cmd_name)
                        logger.debug('Found alias: {} | {}'.format(cmd_name, cmd_alias_name))
                        self.alias_dict[cmd_name] = cmd_alias_name
                        logger.debug('Alias dict is: {}'.format(self.alias_dict))

                    # set to true and break if read successful.
                    logger.debug("Successfully read config file: {}".format(config_file))
                    read_successful = True
                    self.config_file = config_file
                    break
            except OSError:
                # handling file open/read errors
                logger.debug("Can not access config file: {}".format(config_file))
                continue
            except ConfigParser.Error as err:
                # handling ConfigParser errors
                logger.warning(err.message)
                continue

        return read_successful

    def _create_default_config_file(self):
        """Creates a user settings file under USER_SETTINGS_DIR with default hard-coded values."""
        try:
            # make sure folder exists or can be created if not
            assert_folder(USER_SETTINGS_DIR)
        except OSError as err:
            # can not create defaule USER_SETTINGS_DIR under USER_TEMP_DIR
            logger.debug('Can not create config file folder under: {}'.format(USER_SETTINGS_DIR))
            raise ConfigFileError(err.message)

        try:
            with open(self.user_config_file, 'w') as udfile:
                cparser = ConfigParser.ConfigParser()

                # GLOBAL_SETTINGS_SECTION_NAME
                cparser.add_section(GLOBAL_SETTINGS_SECTION_NAME)
                cparser.set(GLOBAL_SETTINGS_SECTION_NAME,
                            VERBOSE_KEY, KEY_VALUE_TRUE if self.verbose else KEY_VALUE_FALSE)
                cparser.set(GLOBAL_SETTINGS_SECTION_NAME,
                            DEBUG_KEY_DEFAULT, self.debug)

                # INIT_SETTINGS_SECTION_NAME
                cparser.add_section(INIT_SETTINGS_SECTION_NAME)
                cparser.set(INIT_SETTINGS_SECTION_NAME,
                            LOG_SCRIPT_USAGE_KEY, KEY_VALUE_TRUE if self.logScriptUsage else KEY_VALUE_FALSE)
                cparser.set(INIT_SETTINGS_SECTION_NAME,
                            ARCHIVE_LOG_FOLDER_KEY, self.archivelogfolder)
                cparser.write(udfile)
                logger.debug('Config file saved under with default settings.')
                logger.debug('Config file saved under: {}'.format(USER_SETTINGS_DIR))
                self.config_file = self.user_config_file

        except OSError:
            # handling file open/save errors
            logger.debug('Can not create config file under: {}'.format(USER_SETTINGS_DIR))
            logger.debug('Skipping saving config file.')
        except ConfigParser.Error as err:
            # handling ConfigParser errors
            logger.error(err.message)

    def save_parameter(self,  param_name, param_value):
        # todo: save user param
        try:
            with open(self.user_config_file, 'w') as udfile:
                cparser = ConfigParser.ConfigParser()
                pass
        except OSError:
            raise ConfigFileError('Error reading file.')
        except ConfigParser.Error as err:
            raise ConfigFileError(err.message)

    def load_parameters(self):
        # todo: load user param
        pass

    def get_alias(self, original_name, type_id):
        try:
            return self.alias_dict[original_name.lower() + type_id.lower()]
        except KeyError:
            return original_name


# creating an instance of _PyRevitUserSettings().
# this pushes reading settings at first import of this module.
user_settings = _PyRevitUserSettings()
