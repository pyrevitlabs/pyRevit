""" Module name = config.py
Copyright (c) 2014-2016 Ehsan Iran-Nejad
Python scripts for Autodesk Revit

This file is part of pyRevit repository at https://github.com/eirannejad/pyRevit

pyRevit is a free set of scripts for Autodesk Revit: you can redistribute it and/or modify
it under the terms of the GNU General Public License version 3, as published by
the Free Software Foundation.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

See this link for a copy of the GNU General Public License protecting this package.
https://github.com/eirannejad/pyRevit/blob/master/LICENSE


~~~
Provides default values for the pyRevit library.
"""

import os
import os.path as op

from System.Diagnostics import Process as _Process
from System import AppDomain as _Appdomain


_VER_MAJOR = 4
_VER_MINOR = 0
_VER_PATCH = 0


# Addon defaults -------------------------------------------------------------------------------------------------------
PYREVIT_ASSEMBLY_NAME = 'pyRevit'
PYREVIT_INIT_SCRIPT_NAME = 'pyRevitLoader'

LOADER_ADDIN = 'PyRevitLoader'
LOADER_ADDIN_COMMAND_INTERFACE_CLASS_EXT = LOADER_ADDIN + '.PyRevitCommand'


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
    """Return the pyRevitLoader.py full directory address"""
    try:
        current_file_path = __file__
        folder = op.dirname(op.dirname(op.dirname(current_file_path)))  # three steps back for /loader/Lib/pyRevit
        return folder
    except NameError:
        return None


def _find_home_directory():
    """Return the pyRevit home directory address. This is the
       directory that contains the loader, pyRevit.package, and other folders"""
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


def _get_host_version():
    """Returns the host Revit version number in format: YYYY"""
    return __revit__.Application.VersionNumber


def _find_git_dir():
    # todo is portable git needed? (run a search for all mentions)
    return op.join(_find_home_directory(), '__git__', 'cmd')


def _get_session_log_file_path():
    """Returns full address of this session's log file."""
    return op.join(USER_TEMP_DIR, SESSION_LOG_FILE_NAME)


# general defaults -----------------------------------------------------------------------------------------------------
LOADER_DIR = _find_loader_directory()
HOME_DIR = _find_home_directory()
USER_TEMP_DIR = _find_user_temp_directory()
REVIT_UNAME = _get_username()
USER_ROAMING_DIR = _find_user_roaming_appdata()
USER_SETTINGS_DIR = _find_user_roaming_appdata_pyrevit()
REVIT_VERSION = _get_host_version()

# new session defaults -------------------------------------------------------------------------------------------------
SESSION_ID = "{}{}_{}".format(PYREVIT_ASSEMBLY_NAME, REVIT_VERSION, REVIT_UNAME)
# creating a session id that is stamped with the process id of the Revit session.
# This id is unique for all python scripts running under this session.
# Previously the session id was stamped by formatted time
# SESSION_STAMPED_ID = "{}_{}".format(SESSION_ID, datetime.now().strftime('%y%m%d%H%M%S'))
SESSION_STAMPED_ID = "{}_{}".format(SESSION_ID, _Process.GetCurrentProcess().Id)

# creating log file name from stamped session id
ASSEMBLY_FILE_TYPE = '.dll'
LOG_FILE_TYPE = '.log'
SESSION_LOG_FILE_NAME = SESSION_STAMPED_ID + LOG_FILE_TYPE
SESSION_LOG_FILE_PATH = _get_session_log_file_path()
LOG_ENTRY_DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
REVISION_EXTENSION = '_R{}'

HOST_ADSK_PROCESS_NAME = _Process.GetCurrentProcess().ProcessName

# caching tabs, panels, buttons and button groups ----------------------------------------------------------------------
SUB_CMP_KEY = '_sub_components'
HASH_VALUE_PARAM = 'hash_value'
HASH_VERSION_PARAM = 'hash_version'

# parsing tabs, panels, buttons and button groups ----------------------------------------------------------------------
PACKAGE_POSTFIX = '.package'
TAB_POSTFIX = '.tab'
PANEL_POSTFIX = '.panel'
LINK_BUTTON_POSTFIX = '.linkbutton'
PUSH_BUTTON_POSTFIX = '.pushbutton'
TOGGLE_BUTTON_POSTFIX = '.toggle'
PULLDOWN_BUTTON_POSTFIX = '.pulldown'
STACKTHREE_BUTTON_POSTFIX = '.stack3'
STACKTWO_BUTTON_POSTFIX = '.stack2'
SPLIT_BUTTON_POSTFIX = '.splitbutton'
SPLITPUSH_BUTTON_POSTFIX = '.splitpushbutton'

SEPARATOR_IDENTIFIER = '---'
SLIDEOUT_IDENTIFIER = '>>>'

ICON_FILE_FORMAT = '.png'
SCRIPT_FILE_FORMAT = '.py'

DEFAULT_ICON_FILE = 'icon' + ICON_FILE_FORMAT
DEFAULT_ON_ICON_FILE = 'on' + ICON_FILE_FORMAT
DEFAULT_OFF_ICON_FILE = 'off' + ICON_FILE_FORMAT
DEFAULT_SCRIPT_FILE = 'script' + SCRIPT_FILE_FORMAT
DEFAULT_CONFIG_SCRIPT_FILE = 'config' + SCRIPT_FILE_FORMAT

DEFAULT_LAYOUT_FILE_NAME = '_layout'

DOCSTRING_PARAM = '__doc__'
AUTHOR_PARAM = '__author__'
SCRIPT_TIME_SAVED_PARAM = '__timesaved__'
MIN_REVIT_VERSION_PARAM = '__min_req_revit_ver__'
MIN_PYREVIT_VERSION_PARAM = '__min_req_pyrevit_ver__'

COMPONENT_LIB_NAME = 'Lib'

# character replacement list for cleaning up file names
SPECIAL_CHARS = {' ': '',
                 '~': '',
                 '!': 'EXCLAM',
                 '@': 'AT',
                 '#': 'NUM',
                 '$': 'DOLLAR',
                 '%': 'PERCENT',
                 '^': '',
                 '&': 'AND',
                 '*': 'STAR',
                 '+': 'PLUS',
                 ';': '', ':': '', ',': '', '\"': '', '{': '', '}': '', '[': '', ']': '', '\(': '', '\)': '',
                 '-': 'MINUS',
                 '=': 'EQUALS',
                 '<': '', '>': '',
                 '?': 'QMARK',
                 '.': 'DOT',
                 '_': 'UNDERS',
                 '|': 'VERT',
                 '\/': '', '\\': ''}

# script internal parameters set by loader module ----------------------------------------------------------------------
FORCED_DEBUG_MODE_PARAM = __forceddebugmode__

# creating ui for tabs, panels, buttons and button groups --------------------------------------------------------------
ICON_SMALL_SIZE = 16
ICON_MEDIUM_SIZE = 24
ICON_LARGE_SIZE = 32
SPLITPUSH_BUTTON_SYNC_PARAM = 'IsSynchronizedWithCurrentItem'

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
ALIAS_SECTION_NAME = 'alias'

VERBOSE_KEY = 'verbose'
LOG_SCRIPT_USAGE_KEY = 'logScriptUsage'
DEBUG_KEY = 'debug'
ARCHIVE_LOG_FOLDER_KEY = 'archivelogfolder'

VERBOSE_KEY_DEFAULT = False
LOG_SCRIPT_USAGE_KEY_DEFAULT = True
DEBUG_KEY_DEFAULT = False
ARCHIVE_LOG_FOLDER_KEY_DEFAULT = 'C:\\'

KEY_VALUE_TRUE = "true"
KEY_VALUE_FALSE = "false"

# InterScript Communication (ISC) defaults -----------------------------------------------------------------------------

CURRENT_REVIT_APPDOMAIN = _Appdomain.CurrentDomain

PYREVIT_ISC_DICT_NAME = PYREVIT_ASSEMBLY_NAME + '_dictISC'
DEBUG_ISC_NAME = PYREVIT_ASSEMBLY_NAME + '_debugISC'
VERBOSE_ISC_NAME = PYREVIT_ASSEMBLY_NAME + '_verboseISC'
