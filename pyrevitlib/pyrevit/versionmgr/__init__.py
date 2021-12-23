"""Utility functions for managing pyRevit versions.

Example:
    >>> from pyrevit import versionmgr
    >>> v = versionmgr.get_pyrevit_version()
    >>> v.get_formatted()
    ... '4.10-beta2'
"""
import os.path as op

from pyrevit import HOME_DIR, BIN_DIR
from pyrevit import VERSION_MAJOR, VERSION_MINOR, VERSION_PATCH, BUILD_METADATA
from pyrevit import PYREVIT_CLI_PATH
from pyrevit.compat import safe_strtype
from pyrevit import coreutils
from pyrevit.coreutils.logger import get_logger
from pyrevit.coreutils import envvars
from pyrevit.coreutils import git


#pylint: disable=W0703,C0302,C0103
mlogger = get_logger(__name__)


class _PyRevitVersion(object):
    """pyRevit version wrapper.

    Args:
        commit_hash (str): signature
    """
    major = VERSION_MAJOR
    minor = VERSION_MINOR
    patch = VERSION_PATCH
    metadata = BUILD_METADATA
    signature = ''

    def __init__(self, signature):
        self.signature = safe_strtype(signature)[:7]

    def as_int_tuple(self):
        """Returns version as an int tuple (major, minor, patch)"""
        try:
            signature = int(self.patch, 16)
        except Exception:
            signature = 0

        ver_tuple = (_PyRevitVersion.major, _PyRevitVersion.minor, signature)
        return ver_tuple

    def as_str_tuple(self):
        """Returns version as an string tuple ('major', 'minor', 'patch')"""
        ver_tuple = (safe_strtype(_PyRevitVersion.major),
                     safe_strtype(_PyRevitVersion.minor),
                     safe_strtype(self.patch))
        return ver_tuple

    def get_formatted(self, strict=False, extended=False):
        """Returns 'major.minor.patch' in string"""
        formatted_ver = '{}.{}.{}'.format(_PyRevitVersion.major,
                                          _PyRevitVersion.minor,
                                          _PyRevitVersion.patch)

        if not strict and self.metadata:
            formatted_ver += ('.' + self.metadata)

        if extended and not strict:
            formatted_ver += (':' + self.signature)

        return formatted_ver


def get_pyrevit_repo():
    """Return pyRevit repository.

    Returns:
        :obj:`pyrevit.coreutils.git.RepoInfo`: repo wrapper object
    """
    try:
        return git.get_repo(HOME_DIR)
    except Exception as repo_err:
        mlogger.debug('Can not create repo from directory: %s | %s',
                      HOME_DIR, repo_err)


def get_pyrevit_version():
    """Return information about active pyRevit version.

    Returns:
        :obj:`_PyRevitVersion`: version wrapper object
    """
    try:
        return _PyRevitVersion(get_pyrevit_repo().last_commit_hash)
    except Exception as ver_err:
        mlogger.debug('Can not get pyRevit patch number. | %s', ver_err)
        return _PyRevitVersion('')


def get_pyrevit_cli_version():
    """Return version of shipped pyRevit CLI utility.

    Returns:
        str: version string of pyRevit CLI utility binary
    """
    return coreutils.get_exe_version(PYREVIT_CLI_PATH)
