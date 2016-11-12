import sys
import logging

from .config import DEBUG_ISC_NAME, VERBOSE_ISC_NAME, LOADER_ADDIN, FORCED_DEBUG_MODE_PARAM
from .utils import set_interscript_comm_data, get_interscript_comm_data

# custom logger methods (for module consistency and custom adjustments) ------------------------------------------------
def set_level(self, level):
    self.setLevel(level)

def set_verbose_mode(self):
    set_interscript_comm_data(VERBOSE_ISC_NAME, True)
    self.setLevel(logging.INFO)

def set_debug_mode(self):
    set_interscript_comm_data(DEBUG_ISC_NAME, True)
    self.setLevel(logging.DEBUG)

def reset_level(self):
    set_interscript_comm_data(VERBOSE_ISC_NAME, False)
    set_interscript_comm_data(DEBUG_ISC_NAME, False)
    self.setLevel(logging.WARNING)

def get_level(self):
    return self.level

# setting up public logger. this will be imported in with other modules ------------------------------------------------
# todo: add file logging / add option to user settings.
handler = logging.StreamHandler(sys.stdout)

# e.g [assemblies] DEBUG: Can not make command.
formatter = logging.Formatter("[%(module)s] %(levelname)s: %(message)s")
handler.setFormatter(formatter)

logger = logging.getLogger(LOADER_ADDIN)
logger.addHandler(handler)

# Setting session-wide debug/verbose status so other individual scripts know about it.
# individual scripts are run at different time and the level settings need to be set inside current host session
# so they can be retreieved later.
if get_interscript_comm_data(DEBUG_ISC_NAME):
    logger.setLevel(logging.DEBUG)
elif get_interscript_comm_data(VERBOSE_ISC_NAME):
    logger.setLevel(logging.INFO)
else:
    logger.setLevel(logging.WARNING)

# the loader assembly sets FORCED_DEBUG_MODE_PARAM to true if user Shift-clicks on the button
# FORCED_DEBUG_MODE_PARAM will be set by the LOADER_ADDIN_COMMAND_INTERFACE_CLASS_EXT at script runtime
if FORCED_DEBUG_MODE_PARAM:
    logger.setLevel(logging.DEBUG)

# adding custom methods to the logging.Logger class
logging.Logger.set_level = set_level
logging.Logger.set_verbose_mode = set_verbose_mode
logging.Logger.set_debug_mode = set_debug_mode
logging.Logger.reset_level = reset_level
logging.Logger.get_level = get_level

# # new handler
# filehandler = logging.FileHandler('pyrevit.log')
#
# #custom log level for file
# filehandler.setLevel(logging.DEBUG)
# # Custom formater for file
# formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# filehandler.setFormatter(formatter)
#
# logger.addHandler(filehandler)
