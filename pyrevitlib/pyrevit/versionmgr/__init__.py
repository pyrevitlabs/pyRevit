from pyrevit import HOME_DIR, VERSION_MAJOR, VERSION_MINOR, EXEC_PARAMS
from pyrevit.coreutils.logger import get_logger
import pyrevit.coreutils.git as git


logger = get_logger(__name__)


class PyRevitVersion(object):
    """Contains current pyrevit version"""
    major = VERSION_MAJOR
    minor = VERSION_MINOR
    patch = ''

    def __init__(self, patch_number):
        self.patch = str(patch_number)[:7]

    def as_int_tuple(self):
        """Returns version as an int tuple (major, minor, patch)"""
        try:
            patch_number = int(self.patch, 16)
        except:
            patch_number = 0
        ver_tuple = (PyRevitVersion.major, PyRevitVersion.minor, patch_number)
        return ver_tuple

    def as_str_tuple(self):
        """Returns version as an string tuple ('major', 'minor', 'patch')"""
        ver_tuple = (str(PyRevitVersion.major), str(PyRevitVersion.minor), self.patch)
        return ver_tuple

    def get_formatted(self):
        """Returns 'major.minor:patch' in string"""
        return '{}.{}:{}'.format(PyRevitVersion.major, PyRevitVersion.minor, self.patch)


def get_pyrevit_repo():
    try:
        return git.get_repo(HOME_DIR)
    except Exception as repo_err:
        logger.error('Can not create repo from directory: {} | {}'.format(HOME_DIR, repo_err))

if not EXEC_PARAMS.doc_mode:
    try:
        PYREVIT_VERSION = PyRevitVersion(get_pyrevit_repo().last_commit_hash)
    except Exception as ver_err:
        logger.error('Can not get pyRevit patch number. | {}'.format(ver_err))
        PYREVIT_VERSION = PyRevitVersion('?')
else:
    PYREVIT_VERSION = None
