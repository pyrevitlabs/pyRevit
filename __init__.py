""" Filename = __init__.py
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
This is pyRevit's main loader script.
Its purpose is to create an instance of pyRevit.session and call its .load() method.
That would in return start parsing the folders for scripts, create a dll for the commands and
lastly create the pyRevit ui in Revit.
"""

import sys
import os.path as op

import pyRevit.config as cfg                        # import basic configurations.
from pyRevit.logger import logger                   # import logger to log messages to pyRevit log.
from pyRevit.utils import Timer                     # import Timer from standard utils to log the load  time.

import pyRevit.output as output_window              # handles output termina window
from pyRevit.usersettings import user_settings      # handles user settings

import pyRevit.session as this_session              # import session to start loading pyRvit.

# todo: move to RPL
sys.path.append(op.join(op.dirname(__file__), 'Lib'))

# initialize timer
t = Timer()

# set output window size.
output_window.set_width(1100)

# log python version and home directory info.
logger.debug('Running on: {0}'.format(sys.version))
logger.debug('Home Directory is: {0}'.format(cfg.HOME_DIR))
logger.debug('Config file is: {}'.format(user_settings.config_file))

# load pyRevit session.
this_session.load()

# log load time
logger.debug('Load time: {}'.format(t.get_time_hhmmss()))
