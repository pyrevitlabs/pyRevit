import sys
import logging

from .config import DEBUG_ISC_NAME, VERBOSE_ISC_NAME, LOADER_ADDIN, FORCED_DEBUG_MODE_PARAM
from .utils import set_interscript_comm_data, get_interscript_comm_data


class _LoggerWrapper:
    """ Logger Wrapper to extend loggers functionality.
    Usage:
     from logger import logger

    Same calls as regular logger:
     logger.info('Message')             # [INFO]  Message
     logger.debug('Message')            # [DEBUG]  Message

    Set Logging Level/Debug:
     logger.verbose(True)               # Set to Info or higher as default

    Additional Features:
     logger.title('Message'): Outputs lines above and below, uses clean format
     >> =========
     >> Message
     >> =========

     logger.error('Message'): appends errmsg to self.errors.
                              This allows you to check if an error occured,
                              and if it did not, close console window.
     >> [ERROR]  Message
     print(logger.errors)
     >> ['Message']

    # Output graphical window will automatically pop up if any content is printed to it.
    # By default (info.WARNING) output window will pop up to show errors, criticals, and warnings.
    """

    def __init__(self):
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter("[%(levelname)s] %(message)s")
        handler.setFormatter(formatter)

        logger = logging.getLogger(LOADER_ADDIN)
        logger.addHandler(handler)

        handler_title = logging.StreamHandler(sys.stdout)
        formatter_title = logging.Formatter("%(message)s")
        handler_title.setFormatter(formatter_title)

        logger_title = logging.getLogger(LOADER_ADDIN + '_title')
        logger_title.addHandler(handler_title)

        self._logger = logger
        self._logger_title = logger_title
        self.errors = []

        # Setting session-wide debug/verbose status so other individual scripts know about it.
        if get_interscript_comm_data(DEBUG_ISC_NAME):
            self.set_level(logging.DEBUG)
        elif get_interscript_comm_data(VERBOSE_ISC_NAME):
            self.set_level(logging.INFO)
        else:
            self.set_level(logging.WARNING)

        # Set level to DEBUG if user Shift-clicks on the button
        # FORCED_DEBUG_MODE_PARAM will be set by the LOADER_ADDIN_COMMAND_INTERFACE_CLASS_EXT at runtime
        if FORCED_DEBUG_MODE_PARAM:
            self.set_level(logging.DEBUG)

    # log level methods ---------------------------------------------
    def set_level(self, level):
        self._logger.setLevel(level)
        self._logger_title.setLevel(level)

    def set_verbose_mode(self):
        set_interscript_comm_data(VERBOSE_ISC_NAME, True)
        self._logger.setLevel(logging.INFO)
        self._logger_title.setLevel(logging.INFO)

    def set_debug_mode(self):
        set_interscript_comm_data(DEBUG_ISC_NAME, True)
        self._logger.setLevel(logging.DEBUG)
        self._logger_title.setLevel(logging.DEBUG)

    def reset_level(self):
        set_interscript_comm_data(VERBOSE_ISC_NAME, False)
        set_interscript_comm_data(DEBUG_ISC_NAME, False)
        self._logger.setLevel(logging.WARNING)
        self._logger_title.setLevel(logging.WARNING)

    def get_level(self):
        return self._logger.level, self._logger_title.level

    # output methods -----------------------------------------------
    def title(self, msg):
        print('='*100)
        self._logger_title.info(msg)
        print('='*100)

    def info(self, msg):
        self._logger.info(msg)

    def debug(self, msg):
        self._logger.debug(msg)

    def warning(self, msg):
        self._logger.warning(msg)

    def error(self, msg):
        self._logger.error(msg)
        self.errors.append(msg)

    def critical(self, msg):
        self._logger.critical(msg)


logger = _LoggerWrapper()

# fixme add file logging / add option to user settings or use DEBUG mode.
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
