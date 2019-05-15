"""Utility functions for managing pyRevit versions.

Example:
    >>> from pyrevit import versionmgr
    >>> v = versionmgr.get_pyrevit_version()
    >>> v.get_formatted()
    ... '4.10-beta2'
"""
import os.path as op

from pyrevit import HOME_DIR, BIN_DIR
from pyrevit import VERSION_MAJOR, VERSION_MINOR, BUILD_METADATA
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
        patch_number (str): patch value

    """
    major = VERSION_MAJOR
    minor = VERSION_MINOR
    metadata = BUILD_METADATA
    patch = ''

    def __init__(self, patch_number):
        self.patch = safe_strtype(patch_number)[:7]

    def as_int_tuple(self):
        """Returns version as an int tuple (major, minor, patch)"""
        try:
            patch_number = int(self.patch, 16)
        except Exception:
            patch_number = 0
        ver_tuple = (_PyRevitVersion.major, _PyRevitVersion.minor, patch_number)
        return ver_tuple

    def as_str_tuple(self):
        """Returns version as an string tuple ('major', 'minor', 'patch')"""
        ver_tuple = (safe_strtype(_PyRevitVersion.major),
                     safe_strtype(_PyRevitVersion.minor), self.patch)
        return ver_tuple

    def get_formatted(self, nopatch=False):
        """Returns 'major.minor:patch' in string"""
        formatted_ver = '{}.{}{}'.format(_PyRevitVersion.major,
                                         _PyRevitVersion.minor,
                                         _PyRevitVersion.metadata)

        return formatted_ver if (nopatch or not self.patch) \
                             else formatted_ver + ':' + self.patch


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
