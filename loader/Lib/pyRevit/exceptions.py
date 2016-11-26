import sys
import traceback


# General Exceptions
class PyRevitException(Exception):
    """Base class for all pyRevit Exceptions.
    Parameters args and message are derived from Exception class.
    """
    def __str__(self):
        sys.exc_type, sys.exc_value, sys.exc_traceback = sys.exc_info()
        return traceback.format_tb(sys.exc_traceback)[0]


class PyRevitUnknownAssemblyError(PyRevitException):
    pass


class PyRevitUnknownFormatError(PyRevitException):
    pass


class PyRevitLoaderNotFoundError(PyRevitException):
    pass


class PyRevitNoScriptFileError(PyRevitException):
    pass


class PyRevitScriptDependencyError(PyRevitException):
    pass


# UI-Specific Exceptions
class PyRevitUIError(PyRevitException):
    pass


# Cache-Specific Exceptions
class PyRevitCacheError(PyRevitException):
    pass


class PyRevitCacheReadError(PyRevitCacheError):
    pass


class PyRevitCacheWriteError(PyRevitCacheError):
    pass


class PyRevitCacheExpiredError(PyRevitCacheError):
    pass


# Config file parsing exeptions
class ConfigFileError(PyRevitException):
    pass
