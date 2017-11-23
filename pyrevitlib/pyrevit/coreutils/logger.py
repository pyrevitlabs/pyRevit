import sys
import os.path
import logging

from pyrevit import PYREVIT_ADDON_NAME, EXEC_PARAMS
from pyrevit import PYREVIT_VERSION_APP_DIR, PYREVIT_FILE_PREFIX_STAMPED
from pyrevit.coreutils import prepare_html_str
from pyrevit.coreutils import envvars
from pyrevit.coreutils.emoji import emojize

LOG_REC_FORMAT = "%(levelname)s: [%(name)s] %(message)s"
LOG_REC_FORMAT_FILE = "%(asctime)s %(levelname)s: [%(name)s] %(message)s"
LOG_REC_FORMAT_FILE_C = "%(asctime)s %(levelname)s: [<{}> %(name)s] %(message)s"

LOG_REC_FORMAT_HTML = prepare_html_str('<div class="logdefault {0}">{1}</div>')

LOG_REC_CLASS_ERROR = 'logerror'
LOG_REC_FORMAT_ERROR = LOG_REC_FORMAT_HTML.format(LOG_REC_CLASS_ERROR,
                                                  LOG_REC_FORMAT)

LOG_REC_CLASS_WARNING = 'logwarning'
LOG_REC_FORMAT_WARNING = LOG_REC_FORMAT_HTML.format(LOG_REC_CLASS_WARNING,
                                                    LOG_REC_FORMAT)


LOG_REC_CLASS_CRITICAL = 'logcritical'
LOG_REC_FORMAT_CRITICAL = LOG_REC_FORMAT_HTML.format(LOG_REC_CLASS_CRITICAL,
                                                     LOG_REC_FORMAT)


# Setting default global logging level
DEFAULT_LOGGING_LEVEL = logging.WARNING

# must be the same in this file and pyrevit/loader/basetypes/envdict.cs
# this is because the csharp code hasn't been compiled when the
# logger module is imported in the other modules
GLOBAL_LOGGING_LEVEL_ENVVAR = envvars.PYREVIT_ENVVAR_PREFIX + '_LOGGINGLEVEL'
envvars.set_pyrevit_env_var(GLOBAL_LOGGING_LEVEL_ENVVAR, DEFAULT_LOGGING_LEVEL)
GLOBAL_FILELOGGING_ENVVAR = envvars.PYREVIT_ENVVAR_PREFIX + '_FILELOGGING'
envvars.set_pyrevit_env_var(GLOBAL_FILELOGGING_ENVVAR, False)


# Creating default file log name and status
FILE_LOG_FILENAME = '{}.log'.format(PYREVIT_FILE_PREFIX_STAMPED)
FILE_LOG_FILEPATH = os.path.join(PYREVIT_VERSION_APP_DIR, FILE_LOG_FILENAME)
FILE_LOGGING_DEFAULT_STATE = False


# custom logger methods --------------------------------------------------------
# (for module consistency and custom adjustments)
class DispatchingFormatter:
    def __init__(self, log_formatters, log_default_formatter):
        self._formatters = log_formatters
        self._default_formatter = log_default_formatter

    def format(self, record):
        formatter = self._formatters.get(record.levelno,
                                         self._default_formatter)
        return formatter.format(record)


class LoggerWrapper(logging.Logger):
    def __init__(self, *args):
        logging.Logger.__init__(self, *args)
        self._has_errors = False
        self._filelogstate = False
        self._curlevel = DEFAULT_LOGGING_LEVEL

    def _log(self, level, msg, args, exc_info=None, extra=None):
        self._has_errors = (self._has_errors or level >= logging.ERROR)

        # any report other than logging.INFO level,
        # needs to cleanup < and > character to avoid html conflict
        if not isinstance(msg, str):
            msg_str = unicode(msg)
        else:
            msg_str = msg
        # get rid of unicode characters
        msg_str = msg_str.encode('ascii', 'ignore')
        msg_str = msg_str.replace(os.path.sep, '/')
        msg_str = emojize(msg_str)
        if level == logging.INFO:
            msg_str = prepare_html_str(msg_str)

        logging.Logger._log(self, level, msg_str, args,
                            exc_info=exc_info, extra=extra)

    def callHandlers(self, record):
        for hdlr in self.handlers:
            # stream-handler only records based on current level
            if isinstance(hdlr, logging.StreamHandler) \
                and record.levelno >= self._curlevel:
                    hdlr.handle(record)
            # file-handler must record everything
            elif isinstance(hdlr, logging.FileHandler) \
                and self._filelogstate:
                    hdlr.handle(record)

    def isEnabledFor(self, level):
        # update current logging level and file logging state
        self._filelogstate = envvars.get_pyrevit_env_var(GLOBAL_FILELOGGING_ENVVAR)
        self._curlevel = envvars.get_pyrevit_env_var(GLOBAL_LOGGING_LEVEL_ENVVAR)

        # the loader assembly sets EXEC_PARAMS.forced_debug_mode to true if
        # user Ctrl-clicks on the button at script runtime.
        if EXEC_PARAMS.forced_debug_mode:
            self._curlevel = logging.DEBUG

        # if file logging is disabled, return the current logging level
        # but if it's enabled, return the file logging level so the record
        # is generated and logged by file-handler. The stream-handler still
        # outputs the record based on the current logging level
        if self._filelogstate:
            return level >= logging.DEBUG

        return level >= self._curlevel

    @staticmethod
    def _reset_logger_env_vars(log_level):
        envvars.set_pyrevit_env_var(GLOBAL_LOGGING_LEVEL_ENVVAR, log_level)

    def has_errors(self):
        return self._has_errors

    def set_level(self, level):
        self._reset_logger_env_vars(level)

    def set_quiet_mode(self):
        self._reset_logger_env_vars(logging.CRITICAL)

    def set_verbose_mode(self):
        self._reset_logger_env_vars(logging.INFO)

    def set_debug_mode(self):
        self._reset_logger_env_vars(logging.DEBUG)

    def reset_level(self):
        self._reset_logger_env_vars(DEFAULT_LOGGING_LEVEL)

    def get_level(self):
        return envvars.get_pyrevit_env_var(GLOBAL_LOGGING_LEVEL_ENVVAR)


# setting up handlers and formatters -------------------------------------------
stdout_hndlr = logging.StreamHandler(sys.stdout)
# e.g [_parser] DEBUG: Can not create command.
default_formatter = logging.Formatter(LOG_REC_FORMAT)
formatters = {logging.ERROR: logging.Formatter(LOG_REC_FORMAT_ERROR),
              logging.WARNING: logging.Formatter(LOG_REC_FORMAT_WARNING),
              logging.CRITICAL: logging.Formatter(LOG_REC_FORMAT_CRITICAL)}
stdout_hndlr.setFormatter(DispatchingFormatter(formatters, default_formatter))


file_hndlr = logging.FileHandler(FILE_LOG_FILEPATH, mode='a', delay=True)
file_formatter = logging.Formatter(LOG_REC_FORMAT_FILE)
file_hndlr.setFormatter(file_formatter)


def get_stdout_hndlr():
    global stdout_hndlr

    return stdout_hndlr


def get_file_hndlr():
    global file_hndlr

    if EXEC_PARAMS.command_mode:
        cmd_file_hndlr = logging.FileHandler(FILE_LOG_FILEPATH,
                                             mode='a', delay=True)
        logformat = LOG_REC_FORMAT_FILE_C.format(EXEC_PARAMS.command_name)
        file_formatter = logging.Formatter(logformat)
        cmd_file_hndlr.setFormatter(file_formatter)
        return cmd_file_hndlr
    else:
        return file_hndlr


# setting up public logger. this will be imported in with other modules --------
logging.setLoggerClass(LoggerWrapper)


loggers = {}


def get_logger(logger_name):
    if loggers.get(logger_name):
        return loggers.get(logger_name)
    else:
        logger = logging.getLogger(logger_name)    # type: LoggerWrapper
        logger.addHandler(get_stdout_hndlr())
        logger.propagate = False
        logger.addHandler(get_file_hndlr())

        loggers.update({logger_name: logger})
        return logger


def set_file_logging(status):
    envvars.set_pyrevit_env_var(GLOBAL_FILELOGGING_ENVVAR, status)


def loggers_have_errors():
    for logger in loggers.values():
        if logger.has_errors():
            return True
    return False
