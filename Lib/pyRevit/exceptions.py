import os
import os.path as op


class PyRevitException(Exception):
    pass


class PyRevitUnknownAssemblyError(PyRevitException):
    pass


class PyRevitUnknownFileNameFormatError(PyRevitException):
    pass


class PyRevitLoaderNotFoundError(PyRevitException):
    pass


# Cache specific exceptions
class PyRevitCacheError(PyRevitException):
    pass


class PyRevitCacheReadError(PyRevitCacheError):
    pass


class PyRevitCacheExpiredError(PyRevitCacheError):
    pass
