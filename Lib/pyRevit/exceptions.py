from .logger import logger


# General Exceptions
class PyRevitException(Exception):
    pass


class PyRevitUnknownAssemblyError(PyRevitException):
    pass


class PyRevitUnknownFormatError(PyRevitException):
    pass


class PyRevitLoaderNotFoundError(PyRevitException):
    pass


# UI -Specific Exceptions
class RevitRibbonTabExists(PyRevitException):
    pass


class RevitRibbonPanelExists(PyRevitException):
    pass


class RevitRibbonItemExists(PyRevitException):
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
