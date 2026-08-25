"""Runtime-backed logging for pyRevit."""
import io
import logging
import os.path as op
import sys
import threading
import traceback

from pyrevit import EXEC_PARAMS, USER_DESKTOP
from pyrevit.compat import safe_strtype
from pyrevit import coreutils


DEFAULT_LOGGING_LEVEL = logging.WARNING
DEPRECATE_LOG_LEVEL = 25
SUCCESS_LOG_LEVEL = 80

logging.addLevelName(DEPRECATE_LOG_LEVEL, "DEPRECATE")
logging.addLevelName(SUCCESS_LOG_LEVEL, "SUCCESS")


def _resolve_service():
    """Resolve against the active command on every call for persistent engines."""
    try:
        runtime = EXEC_PARAMS.script_runtime
        if runtime:
            service = getattr(runtime, 'LoggerService', None)
            if service is not None:
                return service
        from pyrevit.runtime.types import ScriptLoggerService
        return ScriptLoggerService.GetDefault()
    except Exception:
        return None


def _safe_text(value):
    try:
        return safe_strtype(value)
    except Exception:
        try:
            return safe_strtype(repr(value))
        except Exception:
            return '<unprintable>'


def _format_message(message, args):
    text = _safe_text(message)
    if args:
        try:
            if len(args) == 1 and isinstance(args[0], dict):
                text = text % args[0]
            else:
                text = text % args
        except Exception:
            rendered_args = ' '.join(_safe_text(arg) for arg in args)
            if rendered_args:
                text = '{} {}'.format(text, rendered_args)
    return text.replace(op.sep, '/')


def _format_current_exception():
    exc_type, exc_value, exc_traceback = sys.exc_info()
    if exc_type is None:
        return ''
    try:
        return ''.join(traceback.format_exception(
            exc_type, exc_value, exc_traceback)).rstrip()
    except Exception:
        return _safe_text(exc_value)


def _append_exception(message, exception_text):
    if not exception_text:
        return message
    if not message:
        return exception_text
    return '{}\n{}'.format(message, exception_text)


class LoggerWrapper(object):
    """Small Python facade over the active runtime logging service."""

    def __init__(self, name):
        self.name = name

    def _emit(self, level, message, args=(), exception_text=''):
        service = _resolve_service()
        if service is None:
            return
        rendered = _append_exception(
            _format_message(message, args),
            exception_text)
        try:
            service.Log(self.name, int(level), rendered)
        except Exception:
            pass

    def debug(self, message, *args, **kwargs):
        self._emit(logging.DEBUG, message, args)

    def info(self, message, *args, **kwargs):
        self._emit(logging.INFO, message, args)

    def warning(self, message, *args, **kwargs):
        self._emit(logging.WARNING, message, args)

    warn = warning

    def error(self, message, *args, **kwargs):
        exception_text = _format_current_exception() \
            if kwargs.get('exc_info') else ''
        self._emit(logging.ERROR, message, args, exception_text)

    def exception(self, message, *args, **kwargs):
        self._emit(logging.ERROR, message, args, _format_current_exception())

    def critical(self, message, *args, **kwargs):
        self._emit(logging.CRITICAL, message, args)

    def success(self, message, *args, **kwargs):
        self._emit(SUCCESS_LOG_LEVEL, message, args)

    def deprecate(self, message, *args, **kwargs):
        self._emit(DEPRECATE_LOG_LEVEL, message, args)

    def isEnabledFor(self, level):
        service = _resolve_service()
        if service is None:
            return False
        try:
            return bool(service.IsEnabled(int(level)))
        except Exception:
            return False

    def is_enabled_for(self, level):
        service = _resolve_service()
        if service is None:
            return False
        try:
            return bool(service.IsVisibleEnabled(int(level)))
        except Exception:
            return False

    def has_errors(self):
        service = _resolve_service()
        if service is None:
            return False
        try:
            return bool(service.HasErrors)
        except Exception:
            return False

    def set_level(self, level):
        service = _resolve_service()
        if service is not None:
            service.SetMinimumLevel(int(level))

    def set_quiet_mode(self):
        self.set_level(logging.CRITICAL)

    def set_verbose_mode(self):
        self.set_level(logging.INFO)

    def set_debug_mode(self):
        self.set_level(logging.DEBUG)

    def reset_level(self):
        self.set_level(DEFAULT_LOGGING_LEVEL)

    def get_level(self):
        service = _resolve_service()
        if service is None:
            return DEFAULT_LOGGING_LEVEL
        try:
            return int(service.GetMinimumLevel())
        except Exception:
            return DEFAULT_LOGGING_LEVEL

    def log_parse_except(self, parsed_file, parse_ex):
        err_msg = '<strong>Error while parsing file:</strong>\n{file}\n' \
                  '<strong>Error type:</strong> {type}\n' \
                  '<strong>Error Message:</strong> {errmsg}\n' \
                  '<strong>Line/Column:</strong> {lineno}/{colno}\n' \
                  '<strong>Line Text:</strong> {linetext}' \
                  .format(file=parsed_file,
                          type=parse_ex.__class__.__name__,
                          errmsg=getattr(parse_ex, 'msg', ''),
                          lineno=getattr(parse_ex, 'lineno', 0),
                          colno=getattr(parse_ex, 'offset', 0),
                          linetext=getattr(parse_ex, 'text', ''))
        self.error(coreutils.prepare_html_str(err_msg))

    def dev_log(self, source, message=''):
        """Append a command-specific developer note on the user's desktop."""
        devlog_fname = '{}.log'.format(
            EXEC_PARAMS.command_uniqueid or self.name)
        with io.open(op.join(USER_DESKTOP, devlog_fname), 'a', encoding='utf-8') \
                as devlog_file:
            devlog_file.write(
                '{tstamp} [{exid}] {src}: {msg}\n'.format(
                    tstamp=EXEC_PARAMS.exec_timestamp,
                    exid=EXEC_PARAMS.exec_id,
                    src=_safe_text(source),
                    msg=_safe_text(message)))


class _RuntimeLoggingHandler(logging.Handler):
    """Forward root-propagated standard records without applying policy."""

    _pyrevit_runtime_bridge = True
    _emitting = threading.local()

    def emit(self, record):
        if getattr(self._emitting, 'active', False):
            return

        self._emitting.active = True
        try:
            try:
                message = record.getMessage()
            except Exception:
                message = _format_message(record.msg, record.args or ())

            if record.exc_info:
                try:
                    exc_text = ''.join(traceback.format_exception(
                        *record.exc_info)).rstrip()
                except Exception:
                    exc_text = _safe_text(record.exc_info[1])
                message = _append_exception(_safe_text(message), exc_text)

            service = _resolve_service()
            if service is not None:
                service.Log(record.name, int(record.levelno), _safe_text(message))
        except Exception:
            pass
        finally:
            self._emitting.active = False


def _install_standard_logging_bridge():
    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        if getattr(handler, '_pyrevit_runtime_bridge', False):
            return handler

    handler = _RuntimeLoggingHandler()
    handler.setLevel(logging.NOTSET)
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.DEBUG)
    return handler


loggers = {}


def get_logger(logger_name):
    """Return the cached runtime-backed facade for ``logger_name``."""
    logger = loggers.get(logger_name)
    if logger is None:
        logger = LoggerWrapper(logger_name)
        loggers[logger_name] = logger
    return logger


def set_file_logging(status):
    """Enable or disable the runtime-owned default log file."""
    service = _resolve_service()
    if service is not None:
        service.SetFileLogging(bool(status))


def loggers_have_errors():
    """Return whether the active runtime logging service recorded an error."""
    service = _resolve_service()
    if service is None:
        return False
    try:
        return bool(service.HasErrors)
    except Exception:
        return False


def get_runtime_logfile_path():
    """Return the path of the current session's default runtime log file.

    Resolved by the runtime logging service so callers always agree with where
    the file is actually written. Returns None if it can't be determined.
    """
    try:
        from pyrevit.runtime.types import ScriptLoggerService
        return ScriptLoggerService.GetDefaultLogFilePath() or None
    except Exception:
        return None


_install_standard_logging_bridge()
