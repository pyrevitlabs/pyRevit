import sys
import logging

class _LoggerWrapper:
    """ Logger Wrapper to extend loggers functionality.
    Usage:
     from logger import LoggerWrapper

     logger = LoggerWrapper()  #  Initialized loger

    Same calls as regular logger:
     logger.info('Message')
     >> [INFO]  Message

     logger.debug('Message')
     >> [DEBUG]  Message

    Set Logging Level/Debug:
     logger.verbose(True)  # Set to Info or higher as default

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

    # Hides windows if not errors have occured.
     if not logger.errors:
        __window__.Close()
    """

    def __init__(self):

        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter("[%(levelname)s] %(message)s")
        handler.setFormatter(formatter)

        logger = logging.getLogger('pyrevitloader')
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        handler_title = logging.StreamHandler(sys.stdout)
        formatter_title = logging.Formatter("%(message)s")
        handler_title.setFormatter(formatter_title)

        logger_title = logging.getLogger('pyrevitloader_title')
        logger_title.addHandler(handler_title)
        logger_title.setLevel(logging.INFO)

        self._logger = logger
        self._logger_title = logger_title
        self.errors = []

    def verbose(self, verbose):
        if verbose:
            self._logger.setLevel(logging.DEBUG)
        else:
            self._logger.setLevel(logging.INFO)

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

    def set_level(self, level):
        self._logger.setLevel(level)


logger = _LoggerWrapper()
#
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
