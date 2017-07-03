"""
pyRevit root level config for all pyrevit sub-modules.
Sub-modules handle their specific configuration internally.

"""

import clr
import sys
import os
import os.path as op
import traceback
import __builtin__

# noinspection PyUnresolvedReferences
from System.Diagnostics import Process
# noinspection PyUnresolvedReferences
from System.IO import IOException


PYREVIT_ADDON_NAME = 'pyRevit'
VERSION_MAJOR = 4
VERSION_MINOR = 3


# ------------------------------------------------------------------------------
# Base Exceptions
# ------------------------------------------------------------------------------
TRACEBACK_TITLE = 'Traceback:'


# General Exceptions
class PyRevitException(Exception):
    """Base class for all pyRevit Exceptions.
    Parameters args and message are derived from Exception class.
    """
    def __str__(self):
        sys.exc_type, sys.exc_value, sys.exc_traceback = sys.exc_info()
        try:
            tb_report = traceback.format_tb(sys.exc_traceback)[0]
            if self.args:
                message = self.args[0]
                return '{}\n\n{}\n{}'.format(message,
                                             TRACEBACK_TITLE,
                                             tb_report)
            else:
                return '{}\n{}'.format(TRACEBACK_TITLE, tb_report)
        except:
            # noinspection PyArgumentList
            return Exception.__str__(self)


class PyRevitIOError(PyRevitException):
    pass


# ------------------------------------------------------------------------------
# testing for availability of __revit__ just in case and collect host info
# ------------------------------------------------------------------------------
class _HostApplication:
    """Contains current host version and provides comparison functions."""
    def __init__(self):
        # define HOST_SOFTWARE
        try:
            # noinspection PyUnresolvedReferences
            self.uiapp = __revit__
            self.app = self.uiapp.Application
        except Exception:
            raise Exception('Critical Error: Host software is not supported. '
                            '(__revit__ handle is not available)')

    @property
    def version(self):
        return self.app.VersionNumber

    @property
    def version_name(self):
        return self.app.VersionName

    @property
    def build(self):
        return self.app.VersionBuild

    @property
    def username(self):
        """Return the username from Revit API (Application.Username)"""
        uname = self.app.Username
        uname = uname.split('@')[0]  # if username is email
        # removing dots since username will be used in file naming
        uname = uname.replace('.', '')
        return uname

    @property
    def proc(self):
        return Process.GetCurrentProcess()

    @property
    def proc_id(self):
        return Process.GetCurrentProcess().Id

    @property
    def proc_name(self):
        return Process.GetCurrentProcess().ProcessName

    @property
    def proc_screen(self):
        clr.AddReferenceByPartialName('System.Windows.Forms')
        # noinspection PyUnresolvedReferences
        from System.Windows.Forms import Screen
        return Screen.FromHandle(Process.GetCurrentProcess().MainWindowHandle)

    def is_newer_than(self, version):
        return int(self.version) > int(version)

    def is_older_than(self, version):
        return int(self.version) < int(version)


HOST_APP = _HostApplication()


# ------------------------------------------------------------------------------
# Testing values of builtin parameters set in scope by C# Script Executor.
# ------------------------------------------------------------------------------
class _ExecutorParams(object):
    @property   # read-only
    def engine(self):
        """
        Reference to IronPython dotnet ScriptEngine that is
        executing this script.

        Returns:
            Microsoft.Scripting.Hosting.ScriptEngine:
                Reference to dotnet object of this type
        """
        try:
            # noinspection PyUnresolvedReferences
            return __ipyengine__
        except:
            raise AttributeError()

    # @property   # read-only
    # def executor_version(self):
    #     try:
    #         # noinspection PyUnresolvedReferences
    #         for custom_attr in __assmcustomattrs__:
    #             if 'AssemblyPyRevitVersion' in
    #             unicode(custom_attr.AttributeType):
    #                 return unicode(custom_attr.ConstructorArguments[0])
    #                        .replace('\"', '')
    #     except:
    #         raise AttributeError()

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

    @property
    def command_data(self):
        try:
            # noinspection PyUnresolvedReferences
            return __commandData__
        except:
            return None

    @property
    def doc_mode(self):
        try:
            # noinspection PyUnresolvedReferences
            return __sphinx__
        except:
            return False

    @property
    def command_mode(self):
        return self.command_name

    @property
    def result_dict(self):
        try:
            # noinspection PyUnresolvedReferences
            return __result__
        except:
            return False


EXEC_PARAMS = _ExecutorParams()

# if no output window is set by the executor, it means that pyRevit
# is loading at Revit startup (not reloading)
FIRST_LOAD = True if EXEC_PARAMS.window_handle is None else False


# ------------------------------------------------------------------------------
# config environment info
# ------------------------------------------------------------------------------
def _find_home_directory():
    """Return the pyRevitLoader.py full directory address"""
    try:
        # 3 steps back for <home>/Lib/pyrevit
        return op.dirname(op.dirname(op.dirname(__file__)))
    except NameError:
        raise Exception('Critical Error. Can not find home directory.')


# main pyrevit repo folder
HOME_DIR = _find_home_directory()

# main pyrevit lib folders
MAIN_LIB_DIR = op.join(HOME_DIR, 'pyrevitlib')
PYTHON_LIB_DIR = op.join(HOME_DIR, 'pylib')
PYTHON_LIB_SITEPKGS_DIR = op.join(PYTHON_LIB_DIR, 'site-packages')
MISC_LIB_DIR = op.join(HOME_DIR, 'lib')

# default extension extensions folder
EXTENSIONS_DEFAULT_DIR = op.join(HOME_DIR, 'extensions')

# user env paths
USER_ROAMING_DIR = os.getenv('appdata')
USER_SYS_TEMP = os.getenv('temp')
USER_DESKTOP = op.expandvars('%userprofile%\\desktop')


if EXEC_PARAMS.doc_mode:
    PYREVIT_APP_DIR = PYREVIT_VERSION_APP_DIR = ' '
else:
    # pyrevit file directory
    PYREVIT_APP_DIR = op.join(USER_ROAMING_DIR, PYREVIT_ADDON_NAME)
    PYREVIT_VERSION_APP_DIR = op.join(PYREVIT_APP_DIR, HOST_APP.version)

for pyrvt_app_dir in [PYREVIT_APP_DIR, PYREVIT_VERSION_APP_DIR]:
    if not op.isdir(pyrvt_app_dir):
        try:
            os.mkdir(pyrvt_app_dir)
            sys.path.append(pyrvt_app_dir)
        except (OSError, IOException) as err:
            raise PyRevitException('Can not access pyRevit folder at: {} | {}'
                                   .format(pyrvt_app_dir, err))


if EXEC_PARAMS.doc_mode:
    PYREVIT_FILE_PREFIX_UNIVERSAL = None
    PYREVIT_FILE_PREFIX = None
    PYREVIT_FILE_PREFIX_STAMPED = None
else:
    # pyrevit standard files prefix
    PYREVIT_FILE_PREFIX_UNIVERSAL = '{}'.format(PYREVIT_ADDON_NAME)

    PYREVIT_FILE_PREFIX = '{}_{}'.format(PYREVIT_ADDON_NAME,
                                         HOST_APP.version)

    PYREVIT_FILE_PREFIX_STAMPED = '{}_{}_{}'.format(PYREVIT_ADDON_NAME,
                                                    HOST_APP.version,
                                                    HOST_APP.proc_id)

    # pyrevit standard files prefix, with usernames
    PYREVIT_FILE_PREFIX_UNIVERSAL_USER = '{}_{}'.format(PYREVIT_ADDON_NAME,
                                                        HOST_APP.username)

    PYREVIT_FILE_PREFIX_USER = '{}_{}_{}'.format(PYREVIT_ADDON_NAME,
                                                 HOST_APP.version,
                                                 HOST_APP.username)

    PYREVIT_FILE_PREFIX_STAMPED_USER = '{}_{}_{}_{}'.format(PYREVIT_ADDON_NAME,
                                                            HOST_APP.version,
                                                            HOST_APP.username,
                                                            HOST_APP.proc_id)
