"""Core logging module for pyRevit."""
import sys
import os.path as op
import logging

#pylint: disable=W0703,C0302,C0103
from pyrevit import EXEC_PARAMS, USER_DESKTOP
from pyrevit.compat import safe_strtype
from pyrevit import PYREVIT_VERSION_APP_DIR, PYREVIT_FILE_PREFIX_STAMPED
from pyrevit import coreutils
from pyrevit.coreutils import envvars

LOG_REC_FORMAT = "%(levelname)s [%(name)s] %(message)s"
LOG_REC_FORMAT_HEADER = \
    coreutils.prepare_html_str(
        "<strong>%(levelname)s</strong> [%(name)s] %(message)s"
        )
LOG_REC_FORMAT_HEADER_NO_NAME = \
    coreutils.prepare_html_str(
        "<strong>%(levelname)s</strong>\n%(message)s"
        )
LOG_REC_FORMAT_EMOJI = "{emoji} %(levelname)s [%(name)s] %(message)s"
LOG_REC_FORMAT_FILE = "%(asctime)s %(levelname)s [%(name)s] %(message)s"
LOG_REC_FORMAT_FILE_C = "%(asctime)s %(levelname)s [<{}> %(name)s] %(message)s"

LOG_REC_FORMAT_HTML = \
    coreutils.prepare_html_str('<div class="logdefault {style}">{message}</div>')

LOG_REC_CLASS_ERROR = 'logerror'
LOG_REC_FORMAT_ERROR = \
    LOG_REC_FORMAT_HTML.format(style=LOG_REC_CLASS_ERROR,
                               message=LOG_REC_FORMAT_HEADER)

LOG_REC_CLASS_WARNING = 'logwarning'
LOG_REC_FORMAT_WARNING = \
    LOG_REC_FORMAT_HTML.format(style=LOG_REC_CLASS_WARNING,
                               message=LOG_REC_FORMAT_HEADER)

LOG_REC_CLASS_CRITICAL = 'logcritical'
LOG_REC_FORMAT_CRITICAL = \
    LOG_REC_FORMAT_HTML.format(style=LOG_REC_CLASS_CRITICAL,
                               message=LOG_REC_FORMAT_HEADER)

LOG_REC_CLASS_SUCCESS = 'logsuccess'
LOG_REC_FORMAT_SUCCESS = \
    LOG_REC_FORMAT_HTML.format(style=LOG_REC_CLASS_SUCCESS,
                               message=LOG_REC_FORMAT_HEADER_NO_NAME)

LOG_REC_CLASS_DEPRECATE = 'logdeprecate'
LOG_REC_FORMAT_DEPRECATE = \
    LOG_REC_FORMAT_HTML.format(style=LOG_REC_CLASS_DEPRECATE,
                               message=LOG_REC_FORMAT_HEADER_NO_NAME)


# Setting default global logging level
DEFAULT_LOGGING_LEVEL = logging.WARNING

# add deprecate logging level
DEPRECATE_LOG_LEVEL = 25
logging.addLevelName(DEPRECATE_LOG_LEVEL, "DEPRECATE")

# add success logging level
SUCCESS_LOG_LEVEL = 80
logging.addLevelName(SUCCESS_LOG_LEVEL, "SUCCESS")


# must be the same in this file and pyrevit/loader/runtime/envdict.cs
# this is because the csharp code hasn't been compiled when the
# logger module is imported in the other modules
envvars.set_pyrevit_env_var(envvars.LOGGING_LEVEL_ENVVAR,
                            DEFAULT_LOGGING_LEVEL)
envvars.set_pyrevit_env_var(envvars.FILELOGGING_ENVVAR,
                            False)


# Creating default file log name and status
FILE_LOG_FILENAME = '{}runtime.log'.format(PYREVIT_FILE_PREFIX_STAMPED)
FILE_LOG_FILEPATH = op.join(PYREVIT_VERSION_APP_DIR, FILE_LOG_FILENAME)
FILE_LOGGING_DEFAULT_STATE = False


# custom logger methods --------------------------------------------------------
# (for module consistency and custom adjustments)
class DispatchingFormatter(object):
    """Dispatching formatter to format by log level.

    Args:
        log_formatters (dict[int:logging.Formatter]):
            dict of level:formatter key pairs
        log_default_formatter (logging.Formatter): default formatter
    """
    def __init__(self, log_formatters, log_default_formatter):
        self._formatters = log_formatters
        self._default_formatter = log_default_formatter

    def format(self, record):
        """Format given record by log level."""
        formatter = self._formatters.get(record.levelno,
                                         self._default_formatter)
        return formatter.format(record)


class LoggerWrapper(logging.Logger):
    """Custom logging object."""
    def __init__(self, *args):
        logging.Logger.__init__(self, *args)
        self._has_errors = False
        self._filelogstate = False
        self._curlevel = DEFAULT_LOGGING_LEVEL

    def _log(self, level, msg, args, exc_info=None, extra=None): #pylint: disable=W0221
        self._has_errors = (self._has_errors or level >= logging.ERROR)

        # any report other than logging.INFO level,
        # needs to cleanup < and > character to avoid html conflict
        if not isinstance(msg, str):
            msg_str = safe_strtype(msg)
            # get rid of unicode characters
            msg_str = msg_str.encode('ascii', 'ignore')
            msg_str = msg_str.replace(op.sep, '/')
        else:
            msg_str = msg
        logging.Logger._log(self, level, msg_str, args,
                            exc_info=exc_info, extra=extra)

    def callHandlers(self, record):
        """Override logging.Logger.callHandlers."""
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
        """Override logging.Logger.isEnabledFor."""
        # update current logging level and file logging state
        self._filelogstate = \
            envvars.get_pyrevit_env_var(envvars.FILELOGGING_ENVVAR)
        self._curlevel = \
            envvars.get_pyrevit_env_var(envvars.LOGGING_LEVEL_ENVVAR)

        # the loader assembly sets EXEC_PARAMS.debug_mode to true if
        # user Ctrl-clicks on the button at script runtime.
        if EXEC_PARAMS.debug_mode:
            self._curlevel = logging.DEBUG

        # if file logging is disabled, return the current logging level
        # but if it's enabled, return the file logging level so the record
        # is generated and logged by file-handler. The stream-handler still
        # outputs the record based on the current logging level
        if self._filelogstate:
            return level >= logging.DEBUG

        return level >= self._curlevel

    def is_enabled_for(self, level):
        """Check if logger is enabled for level in pyRevit environment."""
        self._curlevel = \
            envvars.get_pyrevit_env_var(envvars.LOGGING_LEVEL_ENVVAR)

        # the loader assembly sets EXEC_PARAMS.debug_mode to true if
        # user Ctrl-clicks on the button at script runtime.
        if EXEC_PARAMS.debug_mode:
            self._curlevel = logging.DEBUG

        return level >= self._curlevel

    @staticmethod
    def _reset_logger_env_vars(log_level):
        envvars.set_pyrevit_env_var(envvars.LOGGING_LEVEL_ENVVAR, log_level)

    def has_errors(self):
        """Check if logger has reported any errors."""
        return self._has_errors

    def set_level(self, level):
        """Set logging level to level."""
        self._reset_logger_env_vars(level)

    def set_quiet_mode(self):
        """Activate quiet mode. All log levels are disabled."""
        self._reset_logger_env_vars(logging.CRITICAL)

    def set_verbose_mode(self):
        """Activate verbose mode. Log levels >= INFO are enabled."""
        self._reset_logger_env_vars(logging.INFO)

    def set_debug_mode(self):
        """Activate debug mode. Log levels >= DEBUG are enabled."""
        self._reset_logger_env_vars(logging.DEBUG)

    def reset_level(self):
        """Reset logging level back to default."""
        self._reset_logger_env_vars(DEFAULT_LOGGING_LEVEL)

    def get_level(self):
        """Return current logging level."""
        return envvars.get_pyrevit_env_var(envvars.LOGGING_LEVEL_ENVVAR)

    def log_parse_except(self, parsed_file, parse_ex):
        """Logs a file parsing exception.

        Args:
            parsed_file (str): File path that failed the parsing
            parse_ex (Exception): Parsing exception
        """
        err_msg = '<strong>Error while parsing file:</strong>\n{file}\n' \
                  '<strong>Error type:</strong> {type}\n' \
                  '<strong>Error Message:</strong> {errmsg}\n' \
                  '<strong>Line/Column:</strong> {lineno}/{colno}\n' \
                  '<strong>Line Text:</strong> {linetext}' \
                  .format(file=parsed_file,
                          type=parse_ex.__class__.__name__,
                          errmsg=parse_ex.msg if hasattr(parse_ex, 'msg') else "",
                          lineno=parse_ex.lineno if hasattr(parse_ex, 'lineno') else 0,
                          colno=parse_ex.offset if hasattr(parse_ex, 'offset') else 0,
                          linetext=parse_ex.text if hasattr(parse_ex, 'text') else "",
                          )
        self.error(coreutils.prepare_html_str(err_msg))

    def success(self, message, *args, **kws):
        """Log a success message.

        Args:
            message (str): success message
            *args (Any): extra agruments passed to the log function
            **kws (Any): extra agruments passed to the log function
        """
        if self.isEnabledFor(SUCCESS_LOG_LEVEL):
            # Yes, logger takes its '*args' as 'args'.
            self._log(SUCCESS_LOG_LEVEL, message, args, **kws)

    def deprecate(self, message, *args, **kws):
        """Log a deprecation message.

        Args:
            message (str): deprecation message
            *args (Any): extra agruments passed to the log function
            **kws (Any): extra agruments passed to the log function
        """
        if self.isEnabledFor(DEPRECATE_LOG_LEVEL):
            # Yes, logger takes its '*args' as 'args'.
            self._log(DEPRECATE_LOG_LEVEL, message, args, **kws)

    def dev_log(self, source, message=''):
        """Appends a message to a log file.

        Args:
            source (str): source of the message
            message (str): message to log
        """
        devlog_fname = \
            '{}.log'.format(EXEC_PARAMS.command_uniqueid or self.name)
        with open(op.join(USER_DESKTOP, devlog_fname), 'a') as devlog_file:
            devlog_file.writelines('{tstamp} [{exid}] {src}: {msg}\n'.format(
                tstamp=EXEC_PARAMS.exec_timestamp,
                exid=EXEC_PARAMS.exec_id,
                src=source,
                msg=message,
                ))


# setting up handlers and formatters -------------------------------------------
stdout_hndlr = logging.StreamHandler(sys.stdout)
# e.g [_parser] DEBUG: Can not create command.
default_formatter = logging.Formatter(LOG_REC_FORMAT)
formatters = {
    SUCCESS_LOG_LEVEL: logging.Formatter(LOG_REC_FORMAT_SUCCESS),
    logging.ERROR: logging.Formatter(LOG_REC_FORMAT_ERROR),
    logging.WARNING: logging.Formatter(LOG_REC_FORMAT_WARNING),
    logging.CRITICAL: logging.Formatter(LOG_REC_FORMAT_CRITICAL),
    DEPRECATE_LOG_LEVEL: logging.Formatter(LOG_REC_FORMAT_DEPRECATE)
    }
stdout_hndlr.setFormatter(DispatchingFormatter(formatters, default_formatter))


file_hndlr = logging.FileHandler(FILE_LOG_FILEPATH, mode='a', delay=True)
file_formatter = logging.Formatter(LOG_REC_FORMAT_FILE)
file_hndlr.setFormatter(file_formatter)


def get_stdout_hndlr():
    """Return stdout logging handler object.

    Returns:
        (logging.StreamHandler):
            configured instance of python's native stream handler
    """
    global stdout_hndlr     #pylint: disable=W0603

    return stdout_hndlr


def get_file_hndlr():
    """Return file logging handler object.

    Returns:
        (logging.FileHandler):
            configured instance of python's native stream handler
    """
    global file_hndlr       #pylint: disable=W0603

    if EXEC_PARAMS.command_mode:
        cmd_file_hndlr = logging.FileHandler(FILE_LOG_FILEPATH,
                                             mode='a', delay=True)
        logformat = LOG_REC_FORMAT_FILE_C.format(EXEC_PARAMS.command_name)
        formatter = logging.Formatter(logformat)
        cmd_file_hndlr.setFormatter(formatter)
        return cmd_file_hndlr
    else:
        return file_hndlr


# setting up public logger. this will be imported in with other modules -------
logging.setLoggerClass(LoggerWrapper)


loggers = {}


def get_logger(logger_name):
    """Register and return a logger with given name.

    Caches all registered loggers and returns the same logger object on
    second call with the same logger name.

    Args:
        logger_name (str): logger name

    Returns:
        (LoggerWrapper): logger object wrapper python's native logger

    Examples:
        ```python
        get_logger('my command')
        ```
        <LoggerWrapper ...>
    """
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
    """Set file logging status (enable/disable).

    Args:
        status (bool): True to enable, False to disable
    """
    envvars.set_pyrevit_env_var(envvars.FILELOGGING_ENVVAR, status)


def loggers_have_errors():
    """Check if any errors have been reported by any of registered loggers."""
    for logger in loggers.values():
        if logger.has_errors():
            return True
    return False
