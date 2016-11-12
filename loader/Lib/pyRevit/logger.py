import sys
import logging

from .config import DEBUG_ISC_NAME, VERBOSE_ISC_NAME, LOADER_ADDIN, FORCED_DEBUG_MODE_PARAM
from .utils import set_interscript_comm_data, get_interscript_comm_data
from .exceptions import PyRevitException


# custom logger methods (for module consistency and custom adjustments) ------------------------------------------------
class LoggerWrapper(logging.Logger):
    def __init__(self, *args):
        logging.Logger.__init__(self, *args)
        self.file_hndlr = None
        self.stdout_hndlr = None
        self.default_log_level = logging.WARNING
        self.entry_format = "[%(module)s] %(levelname)s: %(message)s"

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
        self.setLevel(self.default_log_level)

    def get_level(self):
        return self.level

    def activate_log_to_stdout(self):
        if not self.stdout_hndlr:
            self.stdout_hndlr = logging.StreamHandler(sys.stdout)
            # e.g [parser] DEBUG: Can not create command.
            stdout_formatter = logging.Formatter(self.entry_format)
            self.stdout_hndlr.setFormatter(stdout_formatter)

            self.addHandler(self.stdout_hndlr)
        else:
            raise PyRevitException('A stdout handler already exists: {}'.format(self.stdout_hndlr))

    def activate_log_to_file(self, file_address):
        if not self.file_hndlr:
            self.file_hndlr = logging.FileHandler(file_address)
            # Custom formater for file
            file_formatter = logging.Formatter(self.entry_format)
            self.file_hndlr.setFormatter(file_formatter)

            self.addHandler(self.file_hndlr)
        else:
            raise PyRevitException('A file handler already exists: {}'.format(self.file_hndlr))


# setting up public logger. this will be imported in with other modules ------------------------------------------------

logging.setLoggerClass(LoggerWrapper)
logger = logging.getLogger(LOADER_ADDIN)    # type: LoggerWrapper
logger.activate_log_to_stdout()

# Setting session-wide debug/verbose status so other individual scripts know about it.
# individual scripts are run at different time and the level settings need to be set inside current host session
# so they can be retreieved later.
if get_interscript_comm_data(DEBUG_ISC_NAME):
    logger.set_level(logging.DEBUG)
elif get_interscript_comm_data(VERBOSE_ISC_NAME):
    logger.set_level(logging.INFO)
else:
    logger.reset_level()

# the loader assembly sets FORCED_DEBUG_MODE_PARAM to true if user Shift-clicks on the button
# FORCED_DEBUG_MODE_PARAM will be set by the LOADER_ADDIN_COMMAND_INTERFACE_CLASS_EXT at script runtime
if FORCED_DEBUG_MODE_PARAM:
    logger.set_level(logging.DEBUG)
