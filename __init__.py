import sys
import os.path as op
import logging

# Add library path
sys.path.append(op.join(op.dirname(__file__), 'Lib'))

# now pyrevit module imports
import pyRevit.config as cfg
from pyRevit.logger import logger
from pyRevit.utils import Timer

from pyRevit.usersettings import user_settings
from pyRevit.assemblies import PyRevitCommandsAssembly
from pyRevit.db import PyRevitCommandsTree
from pyRevit.ui import PyRevitUI

__doc__ = 'Searches the script folders and create buttons for the new script or newly installed extensions.'


t = Timer()

if user_settings.verbose:
    # set level to debug if user setting VERBOSE if active
    logger.set_level(logging.DEBUG)
    # and make the output window larger
    # todo move window operations to a module
    __window__.Width = 1100
else:
    # load silently
    __window__.Close()

logger.debug('Running on: {0}'.format(sys.version))
logger.debug('Home Directory is: {0}'.format(cfg.HOME_DIR))

# todo manage exceptions
pyrevit_assembly = PyRevitCommandsAssembly()                                # initiate assembly
db_cmd_tree = PyRevitCommandsTree()                                         # find scripts and populate db
dll_location = pyrevit_assembly.create_dll_assembly(db_cmd_tree)            # create dll for given db of scripts
# todo send the assembly. dllname should be an assembly property
pyrevit_ui = PyRevitUI(db_cmd_tree, dll_location, pyrevit_assembly.name)    # initiate ui for given dll and scripts

if pyrevit_assembly.is_pyrevit_already_loaded():                            # if user is reloading:
    pyrevit_ui.update_ui()                                                     # update ui for given db
else:                                                                       # else:
    pyrevit_ui.create_ui()                                                     # create ui for given db

logger.debug('Load time: {}'.format(t.get_time_hhmmss()))
