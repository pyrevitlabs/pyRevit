"""pyRevit root level config for all pyrevit sub-modules. Sub-modules handle their specific configuration internally."""

import sys
import os
import os.path as op
import traceback
import __builtin__

# noinspection PyUnresolvedReferences
from System.Diagnostics import Process


# ----------------------------------------------------------------------------------------------------------------------
# testing for availability of __revit__ just in case and collect host information
# ----------------------------------------------------------------------------------------------------------------------
class _HostApplication:
    """Contains current host version and provides comparison functions."""
    def __init__(self):
        # define HOST_SOFTWARE
        try:
            # noinspection PyUnresolvedReferences
            self.uiapp = __revit__
        except Exception:
            raise Exception('Critical Error: Host software is not supported. (__revit__ handle is not available)')

    @property
    def version(self):
        return self.uiapp.Application.VersionNumber

    @property
    def username(self):
        """Return the username from Revit API (Application.Username)"""
        uname = self.uiapp.Application.Username
        uname = uname.split('@')[0]  # if username is email
        uname = uname.replace('.', '')  # removing dots since username will be used in file naming
        return uname

    @property
    def proc_id(self):
        return Process.GetCurrentProcess().Id

    @property
    def proc_name(self):
        return Process.GetCurrentProcess().ProcessName

    def is_newer_than(self, version):
        return int(self.version) > int(version)

    def is_older_than(self, version):
        return int(self.version) < int(version)


HOST_APP = _HostApplication()


# ----------------------------------------------------------------------------------------------------------------------
# Testing the values of builtin parameters set in builtins scope by C# Script Executor.
# ----------------------------------------------------------------------------------------------------------------------
class _ExecutorParams(object):
    @property   # read-only
    def engine(self):
        """
        Reference to IronPython dotnet ScriptEngine that is executing this script.

        Returns:
            Microsoft.Scripting.Hosting.ScriptEngine: Reference to dotnet object of this type
        """
        try:
            # noinspection PyUnresolvedReferences
            return __ipyengine__
        except:
            raise AttributeError()

    @property   # read-only
    def executor_version(self):
        try:
            # noinspection PyUnresolvedReferences
            for custom_attr in __assmcustomattrs__:
                if 'AssemblyPyRevitVersion' in str(custom_attr.AttributeType):
                    return str(custom_attr.ConstructorArguments[0]).replace('\"', '')
        except:
            raise AttributeError()

    @property   # read-only
    def forced_debug_mode(self):
        try:
            # noinspection PyUnresolvedReferences
            return __forceddebugmode__
        except:
            return False

    @property   # writeabe
    def window_handle(self):
        try:
            # noinspection PyUnresolvedReferences
            return __window__ if __window__ else None
        except:
            return None

    @window_handle.setter
    def window_handle(self, value):
        __builtin__.__window__ = value

    @property   # writeabe
    def command_name(self):
        try:
            # noinspection PyUnresolvedReferences
            return __commandname__
        except:
            return None

    @command_name.setter
    def command_name(self, value):
        # noinspection PyUnusedLocal
        __builtin__.__commandname__ = value

    @property   # read-only
    def command_path(self):
        try:
            # noinspection PyUnresolvedReferences
            return __commandpath__
        except:
            return None

    @command_path.setter
    def command_path(self, value):
        # noinspection PyUnusedLocal
        __builtin__.__commandpath__ = value

    @property   # read-only
    def executor_version(self):
        try:
            # noinspection PyUnresolvedReferences
            for custom_attr in __assmcustomattrs__:
                if 'AssemblyPyRevitVersion' in str(custom_attr.AttributeType):
                    return str(custom_attr.ConstructorArguments[0]).replace('\"', '')
        except:
            raise AttributeError()

EXEC_PARAMS = _ExecutorParams()


# ----------------------------------------------------------------------------------------------------------------------
# config environment info
# ----------------------------------------------------------------------------------------------------------------------
def _find_home_directory():
    """Return the pyRevitLoader.py full directory address"""
    try:
        return op.dirname(op.dirname(op.dirname(__file__)))   # 3 steps back for <home>/Lib/pyrevit
    except NameError:
        raise Exception('Critical Error. Can not find home directory.')


# main pyrevit repo folder
HOME_DIR = _find_home_directory()

# main pyrevit lib folder
MAIN_LIB_DIR = op.join(HOME_DIR, 'lib')

# default extension extensions folder
EXTENSIONS_DEFAULT_DIR = op.join(HOME_DIR, 'extensions')


PYREVIT_ADDON_NAME = 'pyrevit'
VERSION_MAJOR = 4
VERSION_MINOR = 0


# user env paths
USER_ROAMING_DIR = os.getenv('appdata')
USER_SYS_TEMP = os.getenv('temp')

# pyrevit temp file directory
PYREVIT_APP_DIR = op.join(USER_ROAMING_DIR, 'pyRevit')

# pyrevit standard files prefix
PYREVIT_FILE_PREFIX_UNIVERSAL = '{}_{}'.format(PYREVIT_ADDON_NAME, HOST_APP.username)
PYREVIT_FILE_PREFIX = '{}_{}_{}'.format(PYREVIT_ADDON_NAME,
                                        HOST_APP.version, HOST_APP.username)
PYREVIT_FILE_PREFIX_STAMPED = '{}_{}_{}_{}'.format(PYREVIT_ADDON_NAME,
                                                   HOST_APP.version, HOST_APP.username, HOST_APP.proc_id)

# ----------------------------------------------------------------------------------------------------------------------
# Base Exceptions
# ----------------------------------------------------------------------------------------------------------------------
TRACEBACK_TITLE = 'Traceback:'


# General Exceptions
class PyRevitException(Exception):
    """Base class for all pyRevit Exceptions.
    Parameters args and message are derived from Exception class.
    """
    def __str__(self):
        sys.exc_type, sys.exc_value, sys.exc_traceback = sys.exc_info()
        tb_report = traceback.format_tb(sys.exc_traceback)[0]
        if self.args:
            message = self.args[0]
            return '{}\n\n{}\n{}'.format(message, TRACEBACK_TITLE, tb_report)
        else:
            return '{}\n{}'.format(TRACEBACK_TITLE, tb_report)


class PyRevitIOError(PyRevitException):
    pass
