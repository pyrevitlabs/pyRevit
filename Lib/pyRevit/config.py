import os
import os.path as op
import inspect

_VER_MAJOR = 4
_VER_MINOR = 0
_VER_PATCH = 0

class PyRevitVersion(object):
    """Contains current pyRevit version"""
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


def _find_loader_directory():
    """Return the __init__ full directory address"""
    folder = op.dirname(op.dirname(op.dirname(__file__)))  # three steps back for /__init__/Lib/pyRevit
    return folder


def _find_home_directory():
    """Return the pyRevit home directory address. This is the
       directory that contains the portable git, __init__, pyRevit, and other package_list"""
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


def _get_host_revit_version():
    """Returns the host Revit version number in format: YYYY"""
    return __revit__.Application.VersionNumber


def _find_git_dir():
    return op.join(_find_home_directory(), '__git__', 'cmd')


def _calling_scope_variable(name):
  frame = inspect.stack()[1][0]
  while name not in frame.f_locals:
    frame = frame.f_back
    if frame is None:
      return None
  return frame.f_locals[name]


# general defaults -----------------------------------------------------------------------------------------------------
PYREVIT_ASSEMBLY_NAME = 'pyRevit'
PYREVIT_INIT_SCRIPT_NAME = '__init__'

LOADER_ADDIN = 'RevitPythonLoader'
LOADER_ADDIN_COMMAND_INTERFACE_CLASS_EXT = 'RevitPythonLoader.CommandLoaderBaseExtended'

LOADER_DIR = _find_loader_directory()
HOME_DIR = _find_home_directory()
USER_TEMP_DIR = _find_user_temp_directory()
REVIT_UNAME = _get_username()
USER_ROAMING_DIR = _find_user_roaming_appdata()
USER_SETTINGS_DIR = _find_user_roaming_appdata_pyrevit()
REVIT_VERSION = _get_host_revit_version()

# todo session id needs to be unique for this revit session so every tool running under that session would get the same result.
SESSION_ID = "{}{}_{}".format(PYREVIT_ASSEMBLY_NAME, REVIT_VERSION, REVIT_UNAME)

# parsing tabs, panels, buttons and button groups ----------------------------------------------------------------------
PACKAGE_POSTFIX = '.pkg'
TAB_POSTFIX = '.tab'
PANEL_POSTFIX = '.panel'
LINK_BUTTON_POSTFIX = '.pushbutton'
PUSH_BUTTON_POSTFIX = '.pushbutton'
TOGGLE_BUTTON_POSTFIX = '.toggle'
PULLDOWN_BUTTON_POSTFIX = '.pulldown'
STACKTHREE_BUTTON_POSTFIX = '.stack3'
STACKTWO_BUTTON_POSTFIX = '.stack2'
SPLIT_BUTTON_POSTFIX = '.splitbutton'
SPLITPUSH_BUTTON_POSTFIX = '.splitpushbutton'

ICON_FILE_FORMAT = '.png'
SCRIPT_FILE_FORMAT = '.py'
DEFAULT_ICON_NAME = 'icon' + ICON_FILE_FORMAT
DEFAULT_ON_STATE_ICON_NAME = 'on' + ICON_FILE_FORMAT
DEFAULT_OFF_STATE_ICON_NAME = 'off' + ICON_FILE_FORMAT
DEFAULT_SCRIPT_NAME = 'script' + SCRIPT_FILE_FORMAT

TOOLTIP_PARAM = '__doc__'
AUTHOR_PARAM = '__author__'
# character replacement list for cleaning up file names
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

# portable git and LibGit2Sharp git tools ------------------------------------------------------------------------------
GIT_EXE = '\"' + op.join(_find_git_dir(), 'git.exe') + '\"'
GIT_SUB_FOLDER = '.git'
GIT_LIB = 'LibGit2Sharp'

# user settings defaults -----------------------------------------------------------------------------------------------
SETTINGS_FILE_EXTENSION = '.ini'
ADMIN_DEFAULT_SETTINGS_FILENAME = PYREVIT_INIT_SCRIPT_NAME + SETTINGS_FILE_EXTENSION
USER_DEFAULT_SETTINGS_FILENAME = 'userdefaults' + SETTINGS_FILE_EXTENSION

INIT_SETTINGS_SECTION_NAME = 'init'
GLOBAL_SETTINGS_SECTION_NAME = 'global'
LOG_SCRIPT_USAGE_KEY = "logScriptUsage"
ARCHIVE_LOG_FOLDER_KEY = "archivelogfolder"
ARCHIVE_LOG_FOLDER_DEFAULT = 'C:\\'
VERBOSE_KEY = "verbose"
KEY_VALUE_TRUE = "true"
KEY_VALUE_FALSE = "false"

# getting output window handle -----------------------------------------------------------------------------------------
OUTPUT_WINDOW = _calling_scope_variable('__window__')
