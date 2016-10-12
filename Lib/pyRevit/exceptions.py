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


# Git specific exceptions
class GitError(PyRevitException):
    """Base class for git exceptions."""

    def __init__(self, repo_dir, msg):
        self.repo_dir = repo_dir
        self.repo_name = op.basename(self.repo_dir)
        self.msg = msg
