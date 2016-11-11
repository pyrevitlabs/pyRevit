""" Module name = _assemblies.py
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
Description:
This module provides access to script usage data.
Script usage data is collected through log files. Each script will log its successful execution.
The log file is session-based. All older log files will be archived per settings provided by the user.
The logging system is handled through the loader addin and is inside the C# class for the script command. On startup,
pyRevit assembly make will set the log filename inside each C# class created for script commands.
"""


import os
import os.path as op
import shutil as shutil
from datetime import datetime

from .logger import logger
from .config import USER_TEMP_DIR
from .config import PYREVIT_ASSEMBLY_NAME, LOG_FILE_TYPE, LOG_ENTRY_DATETIME_FORMAT

from .exceptions import PyRevitException
from .usersettings import user_settings

from System.Diagnostics import Process
from System.IO import IOException


def archive_script_usage_logs():
    """Archives older script usage log files to the folder provided by user in user settings.
    :return: None
    """
    if op.exists(user_settings.log_archive_folder):
        host_instances = list(Process.GetProcessesByName('Revit'))
        if len(host_instances) > 1:
            logger.debug('Multiple Revit instance are running...Skipping archiving old log files.')
        elif len(host_instances) == 1:
            logger.debug('Archiving old log files...')
            files = os.listdir(USER_TEMP_DIR)
            for f in files:
                if f.startswith(PYREVIT_ASSEMBLY_NAME) and f.endswith(LOG_FILE_TYPE):
                    try:
                        current_file_path = op.join(USER_TEMP_DIR, f)
                        newloc = op.join(user_settings.log_archive_folder, f)
                        shutil.move(current_file_path, newloc)
                        logger.debug('Existing log file archived to: {}'.format(newloc))
                    except IOException as io_err:
                        logger.warning('Error archiving log file: {} | {}'.format(f, io_err.Message))
                    except Exception as err:
                        logger.warning('Error archiving log file: {} | {}'.format(f, err))
    else:
        logger.debug('Archive log folder does not exist: {}. Skipping...'.format(user_settings.log_archive_folder))


# script usage database interface --------------------------------------------------------------------------------------
class UsageDataEntry:
    """Database entry object."""

    def __init__(self, log_entry):
        """Initialize by a log file entry string.
        Sample log entry:
        2016-10-25 10:51:20, eirannejad, 2016, L:\pyRevitv3\pyRevit\pyRevit.tab\Select_addTaggedElementsToSelection.py
        :type log_entry: str
        """
        try:
            # extract main components
            time_date, self.user_name, self.host_version, script_name_entry = log_entry.split(',', 3)

            # extract datetime
            self.usage_datetime = datetime.strptime(time_date, LOG_ENTRY_DATETIME_FORMAT)

            # extract script directory and name
            # fixme: proper script name extraction for new and legacy scripts
            self.script_directory = op.basename(script_name_entry)
            self.script_name = op.dirname(script_name_entry)
        except Exception as err:
            raise PyRevitException('Error creating entry from string: {}'.format(log_entry))


# Create interface???????? per PEP249 standard: https://www.python.org/dev/peps/pep-0249/
class UsageDatabase:
    def __init__(self):
        self._db = []           # list of UsageDataEntry objects
        self._read_log_files(USER_TEMP_DIR)
        self._read_log_files(user_settings.log_archive_folder)

    def __iter__(self):
        return iter(self._db)

    # data init functions ----------------------------------------------------------------------------------------------
    @staticmethod
    def _verify_log_file(file_name):
        """
        :type file_name: str
        :return :bool
        """
        return PYREVIT_ASSEMBLY_NAME in file_name and file_name.endswith(LOG_FILE_TYPE)

    def _read_log_files(self, log_dir):
        """find all log files in log_dir and reads them line by line and creates database entries
        :type log_dir: str
        :return : None
        """
        logger.debug('Reading log files in: {}'.format(log_dir))
        for parsed_file in os.listdir(log_dir):
            if self._verify_log_file(parsed_file):
                full_log_file = op.join(log_dir, parsed_file)
                logger.debug('Reading log file: {}'.format(full_log_file))
                with open(full_log_file, 'r') as log_file:
                    for line_no, log_entry in enumerate(log_file.read().splitlines()):
                        try:
                            self._db.append(UsageDataEntry(log_entry))
                        except PyRevitException as err:
                            logger.debug('Error creating entry (Line No/Log file): {}/{} | {}'.format(line_no,
                                                                                                      full_log_file,
                                                                                                      err))

    # data query functions ---------------------------------------------------------------------------------------------
    def get_usernames(self):
        """Returns a list of all usenames found in the usage data.
        :return : list
        """
        unames = set()
        for entry in self:  # type: UsageDataEntry
            unames.add(entry.user_name)
        return list(unames)


def get_usagedata_db():
    """Returns an instance of the usagedata database
    :return : UsageDatabase
    """
    return UsageDatabase()
