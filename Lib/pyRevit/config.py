import os
import os.path as op

PYREVIT_ASSEMBLY_NAME = 'pyRevit'
PYREVIT_INIT_SCRIPT_NAME = '__init__'

LOADER_ADDIN = 'RevitPythonLoader'
LOADER_ADDIN_COMMAND_INTERFACE_CLASS_EXT = 'RevitPythonLoader.CommandLoaderBaseExtended'

TAB_POSTFIX = '.tab'
PACKAGE_POSTFIX= '.pkg'
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


# settings for external settings file:
USER_DEFAULT_SETTINGS_FILENAME = "userdefaults.ini"


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
    uname = uname.replace('.','')       # removing dots since username will be used in file naming
    return uname


def _get_user_roaming_appdata():
    """Return %appdata% directory address"""
    return os.getenv('appdata')


def _get_user_roaming_appdata_pyrevit():
    """Return %appdata%/pyRevit directory address"""
    return op.join(_get_user_roaming_appdata(), "pyRevit")


def _get_host_revit_version():
    return __revit__.Application.VersionNumber


LOADER_DIR = _find_loader_directory()
HOME_DIR = _find_home_directory()
USER_TEMP_DIR = _find_user_temp_directory()
REVIT_UNAME = _get_username()
USER_ROAMING_DIR = _get_user_roaming_appdata()
USER_SETTINGS_DIR = _get_user_roaming_appdata_pyrevit()
REVIT_VERSION = _get_host_revit_version()

SESSION_ID = "{}{}_{}".format(PYREVIT_ASSEMBLY_NAME, REVIT_VERSION, REVIT_UNAME)


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


# from os import path
# from tempfile import gettempdir

# from System.Diagnostics import Process

# from loader.logger import logger

# ROOT_DIR = os.getcwd()
# SCRIPTS_DIR = ROOT_DIR
# TEMPDIR = gettempdir()
# LOADER = path.join(SCRIPTS_DIR, '__init__.py')

# # Revit Python Loader Assmebly name and CmdLoader Class
# ASSEMBLY_NAME = 'pyRevitLoader'
# CMD_LOADER_BASE = 'pyRevitLoader.CommandLoaderBase'
# # Name for Scripts DLL
# SCRIPTS_DLL_BASENAME = 'pyrevit_assembly'

# # Unique Per Session
# # SESSION_ID = '{}_session{}'.format(SCRIPTS_DLL_BASENAME,str(Process.GetCurrentProcess().Id))
# CACHE_FILE = '{}_cache'.format(SCRIPTS_DLL_BASENAME)
# logger.info('CWD is {}'.format(ROOT_DIR))

# PKG_IDENTIFIER = '.pkg'


# # pyrevit.tab\PkgMager
# PKGMGR_DIR = os.path.dirname(__file__)

# # pyRevit\pyRevit\pyRevit.tab\
# SCRIPTS_DIR = os.path.dirname(PKGMGR_DIR)

# # pyRevit\pyRevit - this is where pyRevit.tab is
# PYREVIT_DIR = os.path.dirname(SCRIPTS_DIR)

# #  Path fir file version of packages.json
# PKGSJSON_FILEPATH = os.path.join(PKGMGR_DIR, 'packages.json')

# # CHANGE TO PYREVIT REPO
# PKGSJSON_WEB = 'https://raw.githubusercontent.com/gtalarico/pyRevit/pyrevitv3/pyRevit/pyRevit.tab/pkgManager/packages.json'

# #  Very unecessary
# BREAKLINE = '=' * 40

# # Where __git__and __init__ are
# ROOT_DIR = os.path.dirname(PYREVIT_DIR)

# #  Get Git Location
# # PYREVIT_ROOT_DIR = os.path.dirname(PYREVIT_DIR)
# # GIT_EXE = os.path.join(ROOT'__git__', 'cmd', 'git.exe')
# GIT_EXE = os.path.join('__git__', 'cmd', 'git.exe')

# # Changes to directory to root pyrevit dir, so cloned scripts will land there
# os.chdir(ROOT_DIR)
# CWD = os.getcwd()
