"""
Rpw Logger

Usage:

    >>> from rpw.utils.logger import logger
    >>> logger.info('My logger message')
    >>> logger.error('My error message')

"""

import sys


class mockLoggerWrapper():
    def __init__(*args, **kwargs):
        pass

    def __getattr__(self, *args, **kwargs):
        return mockLoggerWrapper(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        pass


class LoggerWrapper():
    """
    Logger Wrapper to extend loggers functionality.
    The logger is called in the same as the regular python logger,
    but also as a few extra features.

    >>> logger.info('Message')
    [INFO]  Message

    Log Title

    >>> logger.title('Message')
    =========
    Message
    =========

    Disable logger

    >>> logger.disable()

    Log Errors: This method appends errmsg to self.errors.
    This allows you to check  if an error occured, and if it did not,
    close console window.

    >>> logger.error('Message')
    [ERROR]  Message
    >>> print(logger.errors)
    ['Message']

    """

    def __init__(self):

        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter("[%(levelname)s] %(message)s")
        # TODO: Show Module
        # formatter = logging.Formatter("[%(levelname)s] %(message)s [%(module)s:%(lineno)s]")
        handler.setFormatter(formatter)

        logger = logging.getLogger('rpw_logger')
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        handler_title = logging.StreamHandler(sys.stdout)
        formatter_title = logging.Formatter("%(message)s")
        handler_title.setFormatter(formatter_title)

        logger_title = logging.getLogger('rpw_logger_title')
        logger_title.addHandler(handler_title)
        logger_title.setLevel(logging.INFO)

        self._logger = logger
        self._logger_title = logger_title
        self.errors = []

    def disable(self):
        """ Sets logger level to logging.CRICITAL """
        self._logger.setLevel(logging.CRITICAL)

    def verbose(self, verbose):
        """
        Sets logger to Verbose.

        Args:
            (bool): True to set `logger.DEBUG`, False to set to `logging.INFO`.

        Usage:
            >>> logger.verbose(True)

        """
        if verbose:
            self._logger.setLevel(logging.DEBUG)
        else:
            self._logger.setLevel(logging.INFO)

    def title(self, msg):
        """ Log Message on logging.INFO level with lines above and below """
        print('=' * 100)
        self._logger_title.info(msg)
        print('=' * 100)

    def info(self, msg):
        """ Log Message on logging.INFO level """
        self._logger.info(msg)

    def debug(self, msg):
        """ Log Message on logging.DEBUG level """
        self._logger.debug(msg)

    def warning(self, msg):
        """ Log Message on logging.WARNING level """
        self._logger.warning(msg)

    def error(self, msg):
        """ Log Message on logging.ERROR level """
        self._logger.error(msg)
        self.errors.append(msg)

    def critical(self, msg):
        """ Log Message on logging.CRITICAL level """
        self._logger.critical(msg)

    def setLevel(self, level):
        self._logger.setLevel(level)

def deprecate_warning(depracated, replaced_by=None):
    msg = '{} has been deprecated and will be removed soon.'.format(depracated)
    if replaced_by:
        msg += ' Use {} instead'.format(replaced_by)
    logger.warning(msg)

try:
    import logging
except ImportError:
    # In Dynamo, Use Mock Logger
    logger = mockLoggerWrapper()
else:
    # In PyRevit, Use Logger
    logger = LoggerWrapper()
