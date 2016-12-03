import pyrevit.coreutils.git as git
from pyrevit import HOME_DIR, _VERSION_MAJOR, _VERSION_MINOR
from pyrevit.coreutils.logger import get_logger


logger = get_logger(__name__)


class PyRevitVersion(object):
    """Contains current pyrevit version"""
    major = _VERSION_MAJOR
    minor = _VERSION_MINOR
    patch = ''

    def __init__(self, patch_number):
        self.patch = str(patch_number)

    @staticmethod
    def as_int_tuple():
        """Returns version as an int tuple (major, minor, patch)"""
        ver_tuple = (PyRevitVersion.major, PyRevitVersion.minor, int(PyRevitVersion.patch, 16))
        return ver_tuple

    @staticmethod
    def as_str_tuple():
        """Returns version as an string tuple ('major', 'minor', 'patch')"""
        ver_tuple = (str(PyRevitVersion.major), str(PyRevitVersion.minor), PyRevitVersion.patch)
        return ver_tuple

    def get_formatted(self):
        """Returns 'major.minor:patch' in string"""
        return '{}.{}:{}'.format(PyRevitVersion.major, PyRevitVersion.minor, self.patch[:7])


def get_pyrevit_repo():
    try:
        return git.get_repo(HOME_DIR)
    except Exception as repo_err:
        logger.error('Can not create repo from directory: {} | {}'.format(HOME_DIR, repo_err))


try:
    PYREVIT_VERSION = PyRevitVersion(get_pyrevit_repo().last_commit_hash)
except:
    PYREVIT_VERSION = PyRevitVersion('?')
