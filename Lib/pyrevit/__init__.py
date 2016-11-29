import os
import os.path as op
import sys

# noinspection PyUnresolvedReferences
from System.Diagnostics import Process

# ----------------------------------------------------------------------------------------------------------------------
# Addon version
# ----------------------------------------------------------------------------------------------------------------------
PYREVIT_ASSEMBLY_NAME = 'pyrevit'

_VER_MAJOR = 4
_VER_MINOR = 0
_VER_PATCH = 0


class PyRevitVersion(object):
    """Contains current pyrevit version"""
    major = _VER_MAJOR
    minor = _VER_MINOR
    patch = _VER_PATCH

    @staticmethod
    def as_int_tuple():
        """Returns version as an int tuple (major, minor, patch)"""
        ver_tuple = (PyRevitVersion.major, PyRevitVersion.minor, PyRevitVersion.patch)
        return ver_tuple

    @staticmethod
    def as_str_tuple():
        """Returns version as an string tuple ('major', 'minor', 'patch')"""
        ver_tuple = (str(PyRevitVersion.major), str(PyRevitVersion.minor), str(PyRevitVersion.patch))
        return ver_tuple

    @staticmethod
    def full_version_as_str():
        """Returns 'major.minor.patch' in string"""
        return str(PyRevitVersion.major) + '.' + str(PyRevitVersion.minor) + '.' + str(PyRevitVersion.patch)

    @staticmethod
    def is_newer_than(version_tuple):
        """:type version_tuple: tuple"""
        try:
            if PyRevitVersion.major > version_tuple[0]:
                return True
            elif PyRevitVersion.major == version_tuple[0]:
                if PyRevitVersion.minor > version_tuple[1]:
                    return True
                elif PyRevitVersion.minor == version_tuple[1]:
                    if PyRevitVersion.patch > version_tuple[2]:
                        return True
        except IndexError:
            raise Exception('Version tuple must be in format: (Major, Minor, Patch)')

        return False

    @staticmethod
    def is_older_than(version_tuple):
        """:type version_tuple: tuple"""
        try:
            if PyRevitVersion.major < version_tuple[0]:
                return True
            elif PyRevitVersion.major == version_tuple[0]:
                if PyRevitVersion.minor < version_tuple[1]:
                    return True
                elif PyRevitVersion.minor == version_tuple[1]:
                    if PyRevitVersion.patch < version_tuple[2]:
                        return True
        except IndexError:
            raise Exception('Version tuple must be in format: (Major, Minor, Patch)')

        return False


# ----------------------------------------------------------------------------------------------------------------------
# testing for availability of __revit__ just in case and collect host information
# ----------------------------------------------------------------------------------------------------------------------

# define HOST_SOFTWARE
try:
    # noinspection PyUnresolvedReferences
    HOST_SOFTWARE = __revit__
except Exception:
    raise Exception('Critical Error. Host software handle is not available (__revit__)')


class _HostVersion:
    """Contains current host version and provides comparison functions."""
    def __init__(self, *args):
        if args:
            self.version = str(args[0])     # type: str
        else:
            self.version = HOST_SOFTWARE.Application.VersionNumber      # type: str

    def is_newer_than(self, version):
        return int(self.version) > int(version)

    def is_older_than(self, version):
        return int(self.version) < int(version)


def _get_username():
    """Return the username from Revit API (Application.Username)"""
    uname = HOST_SOFTWARE.Application.Username
    uname = uname.split('@')[0]  # if username is email
    uname = uname.replace('.', '')  # removing dots since username will be used in file naming
    return uname


HOST_VERSION = _HostVersion()
HOST_USERNAME = _get_username()

HOST_ADSK_PROCESS_NAME = Process.GetCurrentProcess().ProcessName


# ----------------------------------------------------------------------------------------------------------------------
# Testing the value of __forceddebugmode__ (set in builtins scope by C# Script Executor)
# ----------------------------------------------------------------------------------------------------------------------

# define FORCED_DEBUG_MODE_PARAM
# noinspection PyUnresolvedReferences
FORCED_DEBUG_MODE_PARAM = __forceddebugmode__
# noinspection PyUnresolvedReferences
WINDOW_HANDLE_PARAM = __window__
# noinspection PyUnresolvedReferences
COMMAND_NAME_PARAM = __commandname__


# ----------------------------------------------------------------------------------------------------------------------
# environment info
# ----------------------------------------------------------------------------------------------------------------------
def _find_home_directory():
    """Return the pyRevitLoader.py full directory address"""
    try:
        return op.dirname(op.dirname(op.dirname(op.dirname(__file__))))   # 4 steps back for <home>/Lib/pyrevit/config
    except NameError:
        raise Exception('Critical Error. Can not find home directory.')


HOME_DIR = _find_home_directory()


# main pyrevit lib folder
MAIN_LIB_DIR = op.join(HOME_DIR, 'lib')

# default extension extensions folder
EXTENSIONS_DEFAULT_DIR = op.join(HOME_DIR, 'extensions')

# user env paths
USER_ROAMING_DIR = os.getenv('appdata')
USER_SYS_TEMP = os.getenv('temp')

# pyrevit temp file directory
USER_TEMP_DIR = op.join(USER_SYS_TEMP, 'pyrevittemp')
if not op.isdir(USER_TEMP_DIR):
    os.mkdir(USER_TEMP_DIR)

# default directory for user config file
USER_SETTINGS_DIR = op.join(USER_ROAMING_DIR, "pyrevit")

# create a list of all directories that could include extensions
# default is HOME_DIR and EXTENSIONS_DEFAULT_DIR directories
DEFAULT_PKG_SEARCH_DIRS = [HOME_DIR, EXTENSIONS_DEFAULT_DIR]

# define a list of basic folders that need to be added to all scripts
DEFAULT_SYS_PATHS = [MAIN_LIB_DIR]

for path in DEFAULT_SYS_PATHS:
    if path not in sys.path:
        sys.path.append(path)
