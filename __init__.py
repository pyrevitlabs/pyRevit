# __window__.Close()

import sys
import os.path as op

#temp: will take care of this part in RPL
sys.path.append(op.join(op.dirname(__file__), 'Lib'))

# pyrevit module imports
import pyRevit.config as cfg
from pyRevit.logger import logger
from pyRevit.timer import Timer

from pyRevit.assemblies import PyRevitCommandsAssembly
from pyRevit.db import PyRevitCommandsTree
from pyRevit.ui import PyRevitUI

__doc__ = 'Searches the script folders and create buttons for the new script or newly installed extensions.'

# __window__.Width = 1100

t = Timer()
logger.debug('Running on: {0}'.format(sys.version))
logger.debug('Home Directory is: {0}'.format(cfg.HOME_DIR))

pyrevit_assembly = PyRevitCommandsAssembly()                                # initiate assembly
db_cmd_tree = PyRevitCommandsTree()                                         # find scripts and populate db
pyrevit_ui = PyRevitUI()                                                    # initiate ui

dll_location = pyrevit_assembly.create_dll_assembly(db_cmd_tree)            # create dll for given db

if pyrevit_assembly.is_pyrevit_already_loaded():                            # if user is reloading:
    pyrevit_ui.update(db_cmd_tree, dll_location, pyrevit_assembly.name)     #   update ui for given db
else:                                                                       # else:
    pyrevit_ui.create(db_cmd_tree, dll_location, pyrevit_assembly.name)     #   create ui for given db

logger.debug('Load time: {}'.format(t.get_time_hhmmss()))
