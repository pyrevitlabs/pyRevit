import os.path as op

from pyrevit import HOME_DIR, BIN_DIR
from pyrevit import VERSION_MAJOR, VERSION_MINOR, BUILD_METADATA
from pyrevit.compat import safe_strtype
from pyrevit import coreutils
from pyrevit.coreutils.logger import get_logger
from pyrevit.coreutils import envvars
from pyrevit.coreutils import git


#pylint: disable=W0703,C0302,C0103
mlogger = get_logger(__name__)


PYREVIT_VERSION_ENVVAR = envvars.PYREVIT_ENVVAR_PREFIX + '_VERSION'


class PyRevitVersion(object):
    """Contains current pyrevit version"""
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
        ver_tuple = (PyRevitVersion.major, PyRevitVersion.minor, patch_number)
        return ver_tuple

    def as_str_tuple(self):
        """Returns version as an string tuple ('major', 'minor', 'patch')"""
        ver_tuple = (safe_strtype(PyRevitVersion.major),
                     safe_strtype(PyRevitVersion.minor), self.patch)
        return ver_tuple

    def get_formatted(self, nopatch=False):
        """Returns 'major.minor:patch' in string"""
        formatted_ver = '{}.{}{}'.format(PyRevitVersion.major,
                                         PyRevitVersion.minor,
                                         PyRevitVersion.metadata)

        return formatted_ver if (nopatch or not self.patch) \
                             else formatted_ver + ':' + self.patch


def get_pyrevit_repo():
    try:
        return git.get_repo(HOME_DIR)
    except Exception as repo_err:
        mlogger.debug('Can not create repo from directory: %s | %s',
                      HOME_DIR, repo_err)


def get_pyrevit_version():
    try:
        pyrvt_ver = PyRevitVersion(get_pyrevit_repo().last_commit_hash)
    except Exception as ver_err:
        mlogger.debug('Can not get pyRevit patch number. | %s', ver_err)
        pyrvt_ver = PyRevitVersion('')

    envvars.set_pyrevit_env_var(PYREVIT_VERSION_ENVVAR,
                                pyrvt_ver.get_formatted())

    return pyrvt_ver


def get_pyrevit_cli_version():
    return coreutils.get_exe_version(op.join(BIN_DIR, 'pyrevit.exe'))