import os
import os.path as op

PYREVIT_ASSEMBLY_NAME = 'pyRevit'
PYREVIT_INIT_SCRIPT_NAME = '__init__'

ADMIN_DEFAULT_SETTINGS_FILENAME = PYREVIT_INIT_SCRIPT_NAME + ".ini"
USER_DEFAULT_SETTINGS_FILENAME = "userdefaults.ini"


class PyRevitVersion(object):
    """Contains current pyRevit version"""
    major = 3
    minor = 0
    patch = 0

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


def _find_loader_directory():
    """Return the __init__ full directory address"""
    folder = op.dirname(op.dirname(op.dirname(__file__)))  # three steps back for /__init__/Lib/pyRevit
    return folder


def _find_home_directory():
    """Return the pyRevit home directory address. This is the
       directory that contains the portable git, __init__, pyRevit, and other packages"""
    folder = op.dirname(_find_loader_directory())
    return folder


def _find_user_temp_directory():
    """Return the user temp directory %temp%"""
    return os.getenv('Temp')


def _get_username():
    """Return the username from Revit API (Application.Username)"""
    uname = __revit__.Application.Username
    uname = uname.split('@')[0]         # if username is email
    uname = uname.replace('.', '')       # removing dots since username will be used in file naming
    return uname


def _find_user_roaming_appdata():
    """Return %appdata% directory address"""
    return os.getenv('appdata')


def _find_user_roaming_appdata_pyrevit():
    """Return %appdata%/pyRevit directory address"""
    return op.join(_find_user_roaming_appdata(), "pyRevit")


def _find_git_dir():
    return op.join(_find_home_directory(), '__git__', 'cmd')


def _get_host_revit_version():
    """Returns the host Revit version number in format: YYYY"""
    return __revit__.Application.VersionNumber


LOADER_ADDIN = 'RevitPythonLoader'
LOADER_ADDIN_COMMAND_INTERFACE_CLASS_EXT = 'RevitPythonLoader.CommandLoaderBaseExtended'

TAB_POSTFIX = '.tab'
PACKAGE_POSTFIX = '.pkg'
PANEL_BUNDLE_POSTFIX = '.panel'

ICON_FILE_FORMAT = '.png'

LINK_BUTTON_TYPE_NAME = 'PushButton'
PUSH_BUTTON_TYPE_NAME = 'PushButton'
SMART_BUTTON_TYPE_NAME = 'SmartButton'
PULLDOWN_BUTTON_TYPE_NAME = 'PulldownButton'
STACKTHREE_BUTTON_TYPE_NAME = 'Stack3'
STACKTWO_BUTTON_TYPE_NAME = 'Stack2'
SPLIT_BUTTON_TYPE_NAME = 'SplitButton'
SPLITPUSH_BUTTON_TYPE_NAME = 'SplitPushButton'

TOOLTIP_PARAM = '__doc__'
AUTHOR_PARAM = '__author__'
RELOAD_SCRIPTS_OVERRIDE_GROUP_NAME = 'pyRevit'
RELOAD_SCRIPTS_OVERRIDE_SCRIPT_NAME = 'reloadScripts'
MASTER_TAB_NAME = 'master'
SPECIAL_CHARS = {' ': '', '~': '',
                 '!': 'EXCLAM',
                 '@': 'AT',
                 '#': 'NUM',
                 '$': 'DOLLAR',
                 '%': 'PERCENT',
                 '^': '',
                 '&': 'AND',
                 '*': 'STAR',
                 '\(': '', '\)': '',
                 '+': 'PLUS',
                 ';': '', ':': '', ',': '', '\"': '', '{': '', '}': '', '[': '', ']': '',
                 '-': 'MINUS',
                 '=': 'EQUALS',
                 '<': '', '>': '',
                 '?': 'QMARK',
                 '.': 'DOT',
                 '\/': '', '\\': ''}


LOADER_DIR = _find_loader_directory()
HOME_DIR = _find_home_directory()
USER_TEMP_DIR = _find_user_temp_directory()
REVIT_UNAME = _get_username()
USER_ROAMING_DIR = _find_user_roaming_appdata()
USER_SETTINGS_DIR = _find_user_roaming_appdata_pyrevit()
REVIT_VERSION = _get_host_revit_version()

SESSION_ID = "{}{}_{}".format(PYREVIT_ASSEMBLY_NAME, REVIT_VERSION, REVIT_UNAME)

GIT_EXE = '\"' + op.join(_find_git_dir(), 'git.exe') + '\"'
