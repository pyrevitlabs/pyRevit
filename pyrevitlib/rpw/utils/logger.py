"""RPW compatibility wrapper over pyRevit's runtime-backed logger."""
import logging


class mockLoggerWrapper(object):
    def __init__(self, *args, **kwargs):
        self.errors = []

    def __getattr__(self, *args, **kwargs):
        return mockLoggerWrapper(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        pass


class LoggerWrapper(object):
    """Retain RPW's small logger API while delegating output to pyRevit."""

    def __init__(self, runtime_logger):
        self._logger = runtime_logger
        self._level = logging.INFO
        self.errors = []

    def _enabled(self, level):
        return level >= self._level

    def disable(self):
        self._level = logging.CRITICAL

    def verbose(self, verbose):
        self._level = logging.DEBUG if verbose else logging.INFO

    def title(self, msg):
        if self._enabled(logging.INFO):
            self._logger.info('{0}\n{1}\n{0}'.format('=' * 100, msg))

    def info(self, msg, *args):
        if self._enabled(logging.INFO):
            self._logger.info(msg, *args)

    def debug(self, msg, *args):
        if self._enabled(logging.DEBUG):
            self._logger.debug(msg, *args)

    def warning(self, msg, *args):
        if self._enabled(logging.WARNING):
            self._logger.warning(msg, *args)

    def error(self, msg, *args):
        if self._enabled(logging.ERROR):
            self._logger.error(msg, *args)
            self.errors.append(msg)

    def critical(self, msg, *args):
        if self._enabled(logging.CRITICAL):
            self._logger.critical(msg, *args)

    def setLevel(self, level):
        self._level = level


def deprecate_warning(depracated, replaced_by=None):
    msg = '{} has been deprecated and will be removed soon.'.format(depracated)
    if replaced_by:
        msg += ' Use {} instead'.format(replaced_by)
    logger.warning(msg)


try:
    from pyrevit.coreutils.logger import get_logger
except ImportError:
    logger = mockLoggerWrapper()
else:
    logger = LoggerWrapper(get_logger('rpw_logger'))
