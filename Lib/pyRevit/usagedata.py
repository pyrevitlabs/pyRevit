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
Script usage data is collected through a specific log file. Each script will log its successful execution in this log.
The log file is session-based. All older log files will be archived per settings provided by the user.
The logging system is handles through the loader addin and is inside the C# class for the script command. On startup,
pyRevit assembly make will set the log file name inside each C# class created for script commands.
"""


import os
import os.path as op
import shutil as shutil

from .logger import logger
from .config import PYREVIT_ASSEMBLY_NAME, LOG_FILE_TYPE, USER_TEMP_DIR, SESSION_LOG_FILE_NAME

from .usersettings import user_settings

from System.Diagnostics import Process
from System.IO import IOException


def _archive_script_usage_logs():
    if op.exists(user_settings.archivelogfolder):
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
                        newloc = op.join(user_settings.archivelogfolder, f)
                        shutil.move(current_file_path, newloc)
                        logger.debug('Existing log file archived to: {}'.format(newloc))
                    except IOException as io_err:
                        logger.warning('Error archiving log file: {} | {}'.format(f, io_err.Message))
                    except Exception as err:
                        logger.warning('Error archiving log file: {} | {}'.format(f, err))
    else:
        logger.debug('Archive log folder does not exist: {}. Skipping...'.format(user_settings.archivelogfolder))


def _get_log_file_path():
    return op.join(USER_TEMP_DIR, SESSION_LOG_FILE_NAME)


# data query functions -------------------------------------------------------------------------------------------------
# ...
# todo learn about conventional database access methods in python (json maybe?)
