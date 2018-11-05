"""pyRevit root level config for all pyrevit sub-modules.

Examples:
    >>> from pyrevit import DB, UI
    >>> from pyrevit import PyRevitException, PyRevitIOError

    >>> # pyrevit module has global instance of the
    >>> # _HostAppPostableCommand and _ExecutorParams classes already created
    >>> # import and use them like below
    >>> from pyrevit import HOST_APP
    >>> from pyrevit import EXEC_PARAMS
"""
#pylint: disable=W0703,C0302,C0103,C0413
import sys
import os
import os.path as op
from collections import namedtuple
import traceback
import clr  #pylint: disable=E0401


try:
    clr.AddReference('PyRevitLoader')
except Exception:
    # probably older IronPython engine not being able to
    # resolve to an already loaded assembly.
    # PyRevitLoader is executing this script so it should be referabe.
    pass

try:
    import PyRevitLoader
except ImportError:
    # this means that pyRevit is _not_ being loaded from a pyRevit engine
    # e.g. when importing from RevitPythonShell
    PyRevitLoader = None


PYREVIT_ADDON_NAME = 'pyRevit'
VERSION_MAJOR = 4
VERSION_MINOR = 6
BUILD_METADATA = '.5'

# -----------------------------------------------------------------------------
# config environment paths
# -----------------------------------------------------------------------------
# main pyrevit repo folder
try:
    # 3 steps back for <home>/Lib/pyrevit
    HOME_DIR = op.dirname(op.dirname(op.dirname(__file__)))
except NameError:
    raise Exception('Critical Error. Can not find home directory.')

# BIN directory
BIN_DIR = op.join(HOME_DIR, 'bin')

# default extensions directory
EXTENSIONS_DEFAULT_DIR = op.join(HOME_DIR, 'extensions')

# main pyrevit lib folders
MAIN_LIB_DIR = op.join(HOME_DIR, 'pyrevitlib')
MISC_LIB_DIR = op.join(HOME_DIR, 'site-packages')

# path to pyrevit module
MODULE_DIR = op.join(MAIN_LIB_DIR, 'pyrevit')

# loader directory
LOADER_DIR = op.join(MODULE_DIR, 'loader')

# addin directory
ADDIN_DIR = op.join(LOADER_DIR, 'addin')

# if loader module is available means pyRevit is being executed by Revit.
if PyRevitLoader:
    ENGINES_DIR = \
        op.join(BIN_DIR, 'engines', PyRevitLoader.ScriptExecutor.EngineVersion)
    ADDIN_RESOURCE_DIR = op.join(BIN_DIR, 'engines',
                                 'Source', 'pyRevitLoader', 'Resources')
# otherwise it might be under test, or documentation processing.
# so let's keep the symbols but set to None (fake the symbols)
else:
    ENGINES_DIR = ADDIN_RESOURCE_DIR = None

# add the framework dll path to the search paths
sys.path.append(BIN_DIR)
sys.path.append(ADDIN_DIR)
sys.path.append(ENGINES_DIR)


# now we can start importing stuff
from pyrevit.compat import safe_strtype
from pyrevit.framework import Process
from pyrevit.framework import Windows
from pyrevit.framework import Forms
from pyrevit.api import DB, UI

# -----------------------------------------------------------------------------
# Base Exceptions
# -----------------------------------------------------------------------------
TRACEBACK_TITLE = 'Traceback:'


# General Exceptions
class PyRevitException(Exception):
    """Base class for all pyRevit Exceptions.

    Parameters args and message are derived from Exception class.
    """

    @property
    def msg(self):
        """Return exception message."""
        if self.args:
            return self.args[0] #pylint: disable=E1136
        else:
            return ''

    def __str__(self):
        """Process stack trace and prepare report for output window."""
        sys.exc_type, sys.exc_value, sys.exc_traceback = sys.exc_info()
        try:
            tb_report = traceback.format_tb(sys.exc_traceback)[0]
            if self.msg:
                return '{}\n\n{}\n{}'.format(self.msg,
                                             TRACEBACK_TITLE,
                                             tb_report)
            else:
                return '{}\n{}'.format(TRACEBACK_TITLE, tb_report)
        except Exception:
            return Exception.__str__(self)


class PyRevitIOError(PyRevitException):
    """Generic IO error in pyRevit."""

    pass


# -----------------------------------------------------------------------------
# Wrapper for __revit__ builtin parameter set in scope by C# Script Executor
# -----------------------------------------------------------------------------
# namedtuple for passing information about a PostableCommand
_HostAppPostableCommand = namedtuple('_HostAppPostableCommand',
                                     ['name', 'key', 'id', 'rvtobj'])
"""Private namedtuple for passing information about a PostableCommand

Attributes:
    name (str): Postable command name
    key (str): Postable command key string
    id (int): Postable command id
    rvtobj (``RevitCommandId``): Postable command Id Object
"""


class _HostApplication(object):
    """Private Wrapper for Current Instance of Revit.

    Provides version info and comparison functionality, alongside providing
    info on the active screen, active document and ui-document, available
    postable commands, and other functionality.

    Args:
        host_uiapp (``UIApplication``): Instance of running host.

    Example:
        >>> hostapp = _HostApplication(__revit__)
        >>> hostapp.is_newer_than(2017)
    """

    def __init__(self, host_uiapp):
        self._uiapp = host_uiapp
        self._postable_cmds = []

    @property
    def uiapp(self):
        """Return UIApplication provided to the running command."""
        return self._uiapp

    @property
    def app(self):
        """Return Application provided to the running command."""
        return self.uiapp.Application

    @property
    def uidoc(self):
        """Return active UIDocument."""
        return getattr(self.uiapp, 'ActiveUIDocument', None)

    @property
    def doc(self):
        """Return active Document."""
        return getattr(self.uidoc, 'Document', None)

    @property
    def activeview(self):
        """Return view that is active (UIDocument.ActiveView)."""
        return getattr(self.uidoc, 'ActiveView', None)

    @activeview.setter
    def activeview(self, value):
        """Set the active view in user interface."""
        setattr(self.uidoc, 'ActiveView', value)

    @property
    def docs(self):
        """Return :obj:`list` of open :obj:`Document` objects."""
        return getattr(self.app, 'Documents', None)

    @property
    def available_servers(self):
        """Return :obj:`list` of available Revit server names."""
        return list(self.app.GetRevitServerNetworkHosts())

    @property
    def version(self):
        """str: Return version number (e.g. '2018')."""
        return self.app.VersionNumber

    @property
    def subversion(self):
        """str: Return subversion number (e.g. '2018.3')."""
        return self.app.SubVersionNumber

    @property
    def version_name(self):
        """str: Return version name (e.g. 'Autodesk Revit 2018')."""
        return self.app.VersionName

    @property
    def build(self):
        """str: Return build number (e.g. '20170927_1515(x64)')."""
        return self.app.VersionBuild

    @property
    def username(self):
        """str: Return the username from Revit API (Application.Username)."""
        uname = self.app.Username
        uname = uname.split('@')[0]  # if username is email
        # removing dots since username will be used in file naming
        uname = uname.replace('.', '')
        return uname

    @property
    def proc(self):
        """System.Diagnostics.Process: Return current process object."""
        return Process.GetCurrentProcess()

    @property
    def proc_id(self):
        """int: Return current process id."""
        return Process.GetCurrentProcess().Id

    @property
    def proc_name(self):
        """str: Return current process name."""
        return Process.GetCurrentProcess().ProcessName

    @property
    def proc_path(self):
        """str: Return file path for the current process main module."""
        return Process.GetCurrentProcess().MainModule.FileName

    @property
    def proc_screen(self):
        """``intptr``: Return handle to screen hosting current process."""
        return Forms.Screen.FromHandle(
            Process.GetCurrentProcess().MainWindowHandle)

    @property
    def proc_screen_workarea(self):
        """``System.Drawing.Rectangle``: Return screen working area."""
        screen = HOST_APP.proc_screen
        if screen:
            return screen.WorkingArea

    @property
    def proc_screen_scalefactor(self):
        """float: Return scaling for screen hosting current process."""
        screen = HOST_APP.proc_screen
        if screen:
            actual_wdith = Windows.SystemParameters.PrimaryScreenWidth
            scaled_width = screen.PrimaryScreen.WorkingArea.Width
            return abs(scaled_width / actual_wdith)

    def is_newer_than(self, version, or_equal=False):
        """bool: Return True if host app is newer than provided version.

        Args:
            version (str or int): version to check against.
        """
        if or_equal:
            return int(self.version) >= int(version)
        else:
            return int(self.version) > int(version)

    def is_older_than(self, version):
        """bool: Return True if host app is older than provided version.

        Args:
            version (str or int): version to check against.
        """
        return int(self.version) < int(version)

    def is_exactly(self, version):
        """bool: Return True if host app is equal to provided version.

        Args:
            version (str or int): version to check against.
        """
        return int(self.version) == int(version)

    def get_postable_commands(self):
        """Return list of postable commands.

        Returns:
            :obj:`list` of :obj:`_HostAppPostableCommand`
        """
        # if list of postable commands is _not_ already created
        # make the list and store in instance parameter
        if not self._postable_cmds:
            for pc in UI.PostableCommand.GetValues(UI.PostableCommand):
                try:
                    rcid = UI.RevitCommandId.LookupPostableCommandId(pc)
                    self._postable_cmds.append(
                        # wrap postable command info in custom namedtuple
                        _HostAppPostableCommand(name=safe_strtype(pc),
                                                key=rcid.Name,
                                                id=rcid.Id,
                                                rvtobj=rcid)
                        )
                except Exception:
                    # if any error occured when querying postable command
                    # or its info, pass silently
                    pass

        return self._postable_cmds


try:
    # Create an intance of host application wrapper
    # making sure __revit__ is available
    HOST_APP = _HostApplication(__revit__)  #pylint: disable=E0602
except Exception:
    raise Exception('Critical Error: Host software is not supported. '
                    '(__revit__ handle is not available)')


# -----------------------------------------------------------------------------
# Wrapper to access builtin parameters set in scope by C# Script Executor
# -----------------------------------------------------------------------------
class _ExecutorParams(object):
    """Private Wrapper that provides runtime environment info."""

    @property   # read-only
    def engine_mgr(self):
        """``PyRevitBaseClasses.EngineManager``: Return engine manager."""
        try:
            return __ipyenginemanager__
        except NameError:
            raise AttributeError()

    @property   # read-only
    def engine_ver(self):
        """str: Return PyRevitLoader.ScriptExecutor hardcoded version."""
        if PyRevitLoader:
            return PyRevitLoader.ScriptExecutor.EngineVersion

    @property  # read-only
    def first_load(self):
        """bool: Check whether pyrevit is not running in pyrevit command."""
        # if no output window is set by the executor, it means that pyRevit
        # is loading at Revit startup (not reloading)
        return True if EXEC_PARAMS.window_handle is None else False

    @property   # read-only
    def pyrevit_command(self):
        """``PyRevitBaseClasses.PyRevitCommandRuntime``: Return command."""
        try:
            return __externalcommand__
        except NameError:
            return None

    @property   # read-only
    def forced_debug_mode(self):
        """bool: Check if command is in debug mode."""
        if self.pyrevit_command:
            return self.pyrevit_command.DebugMode
        else:
            return False

    @property   # read-only
    def executed_from_ui(self):
        """bool: Check if command was executed from ui."""
        if self.pyrevit_command:
            return self.pyrevit_command.ExecutedFromUI
        else:
            return False

    @property   # read
    def window_handle(self):
        """``PyRevitBaseClasses.ScriptOutput``: Return output window."""
        if self.pyrevit_command:
            return self.pyrevit_command.OutputWindow

    @property   # read-only
    def command_path(self):
        """str: Return current command path."""
        if '__commandpath__' in __builtins__ \
                and __builtins__['__commandpath__']:
            return __builtins__['__commandpath__']
        elif self.pyrevit_command:
            return op.dirname(self.pyrevit_command.ScriptSourceFile)

    @property   # read-only
    def command_alt_path(self):
        """str: Return current command alternate script path."""
        if '__alternatecommandpath__' in __builtins__ \
                and __builtins__['__alternatecommandpath__']:
            return __builtins__['__alternatecommandpath__']
        elif self.pyrevit_command:
            return op.dirname(self.pyrevit_command.AlternateScriptSourceFile)

    @property   # read-only
    def command_name(self):
        """str: Return current command name."""
        if '__commandname__' in __builtins__ \
                and __builtins__['__commandname__']:
            return __builtins__['__commandname__']
        elif self.pyrevit_command:
            return self.pyrevit_command.CommandName

    @property   # read-only
    def command_bundle(self):
        """str: Return current command bundle name."""
        if '__commandbundle__' in __builtins__ \
                and __builtins__['__commandbundle__']:
            return __builtins__['__commandbundle__']
        elif self.pyrevit_command:
            return self.pyrevit_command.CommandBundle

    @property   # read-only
    def command_extension(self):
        """str: Return current command extension name."""
        if '__commandextension__' in __builtins__ \
                and __builtins__['__commandextension__']:
            return __builtins__['__commandextension__']
        elif self.pyrevit_command:
            return self.pyrevit_command.CommandExtension

    @property   # read-only
    def command_uniqueid(self):
        """str: Return current command unique id."""
        if '__commanduniqueid__' in __builtins__ \
                and __builtins__['__commanduniqueid__']:
            return __builtins__['__commanduniqueid__']
        elif self.pyrevit_command:
            return self.pyrevit_command.CommandUniqueId

    @property
    def command_data(self):
        """``ExternalCommandData``: Return current command data."""
        if self.pyrevit_command:
            return self.pyrevit_command.CommandData

    @property
    def doc_mode(self):
        """bool: Check if pyrevit is running by doc generator."""
        try:
            return __sphinx__
        except NameError:
            return False

    @property
    def command_mode(self):
        """bool: Check if pyrevit is running in pyrevit command context."""
        return self.pyrevit_command is not None

    @property
    def result_dict(self):
        """``Dictionary<String, String>``: Return results dict for logging."""
        if self.pyrevit_command:
            return self.pyrevit_command.GetResultsDictionary()


# create an instance of _ExecutorParams wrapping current runtime.
EXEC_PARAMS = _ExecutorParams()


# -----------------------------------------------------------------------------
# config user environment paths
# -----------------------------------------------------------------------------
# user env paths
ALLUSER_PROGRAMDATA = os.getenv('programdata')
USER_ROAMING_DIR = os.getenv('appdata')
USER_SYS_TEMP = os.getenv('temp')
USER_DESKTOP = op.expandvars('%userprofile%\\desktop')
# verify directory per issue #369
if not USER_DESKTOP or not op.exists(USER_DESKTOP):
    USER_DESKTOP = USER_SYS_TEMP

# create paths for pyrevit files
if EXEC_PARAMS.doc_mode:
    PYREVIT_ALLUSER_APP_DIR = PYREVIT_APP_DIR = PYREVIT_VERSION_APP_DIR = ' '
else:
    # pyrevit file directory
    PYREVIT_ALLUSER_APP_DIR = op.join(ALLUSER_PROGRAMDATA, PYREVIT_ADDON_NAME)
    PYREVIT_APP_DIR = op.join(USER_ROAMING_DIR, PYREVIT_ADDON_NAME)
    PYREVIT_VERSION_APP_DIR = op.join(PYREVIT_APP_DIR, HOST_APP.version)

    # add runtime paths to sys.paths
    # this will allow importing any dynamically compiled DLLs that
    # would be placed under this paths.
    for pyrvt_app_dir in [PYREVIT_APP_DIR, PYREVIT_VERSION_APP_DIR]:
        if not op.isdir(pyrvt_app_dir):
            try:
                os.mkdir(pyrvt_app_dir)
                sys.path.append(pyrvt_app_dir)
            except Exception as err:
                raise PyRevitException('Can not access pyRevit '
                                       'folder at: {} | {}'
                                       .format(pyrvt_app_dir, err))
        else:
            sys.path.append(pyrvt_app_dir)


# -----------------------------------------------------------------------------
# standard prefixes for naming pyrevit files (config, appdata and temp files)
# -----------------------------------------------------------------------------
if EXEC_PARAMS.doc_mode:
    PYREVIT_FILE_PREFIX_UNIVERSAL = PYREVIT_FILE_PREFIX = \
        PYREVIT_FILE_PREFIX_STAMPED = None
    PYREVIT_FILE_PREFIX_UNIVERSAL_USER = PYREVIT_FILE_PREFIX_USER = \
        PYREVIT_FILE_PREFIX_STAMPED_USER = None
else:
    # e.g. pyRevit_
    PYREVIT_FILE_PREFIX_UNIVERSAL = '{}'.format(PYREVIT_ADDON_NAME)

    # e.g. pyRevit_2018_
    PYREVIT_FILE_PREFIX = '{}_{}'.format(PYREVIT_ADDON_NAME,
                                         HOST_APP.version)

    # e.g. pyRevit_2018_14422_
    PYREVIT_FILE_PREFIX_STAMPED = '{}_{}_{}'.format(PYREVIT_ADDON_NAME,
                                                    HOST_APP.version,
                                                    HOST_APP.proc_id)

    # e.g. pyRevit_eirannejad_
    PYREVIT_FILE_PREFIX_UNIVERSAL_USER = '{}_{}'.format(PYREVIT_ADDON_NAME,
                                                        HOST_APP.username)

    # e.g. pyRevit_2018_eirannejad_
    PYREVIT_FILE_PREFIX_USER = '{}_{}_{}'.format(PYREVIT_ADDON_NAME,
                                                 HOST_APP.version,
                                                 HOST_APP.username)

    # e.g. pyRevit_2018_eirannejad_14422_
    PYREVIT_FILE_PREFIX_STAMPED_USER = '{}_{}_{}_{}'.format(PYREVIT_ADDON_NAME,
                                                            HOST_APP.version,
                                                            HOST_APP.username,
                                                            HOST_APP.proc_id)
