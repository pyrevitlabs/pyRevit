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
#pylint: disable=W0703,C0302,C0103,C0413,raise-missing-from
import sys
import os
import os.path as op
from collections import namedtuple
import traceback
import re

import clr  #pylint: disable=E0401

from pyrevit import compat

PYREVIT_ADDON_NAME = 'pyRevit'
PYREVIT_CLI_NAME = 'pyrevit.exe'

# extract version from version file
VERSION_STRING = '0.0.'
with open(op.join(op.dirname(__file__), 'version'), 'r') as version_file:
    VERSION_STRING = version_file.read()
matches = re.findall(r'(\d+)\.(\d+)\.(\d+)\.?(.+)?', VERSION_STRING)[0]
if len(matches) == 4:
    VERSION_MAJOR, VERSION_MINOR, VERSION_PATCH, BUILD_METADATA = matches
else:
    VERSION_MAJOR, VERSION_MINOR, VERSION_PATCH = matches
    BUILD_METADATA = ""

try:
    VERSION_MAJOR = int(VERSION_MAJOR)
    VERSION_MINOR = int(VERSION_MINOR)
    VERSION_PATCH = int(VERSION_PATCH)
except:
    raise Exception('Critical Error. Can not determine pyRevit version.')
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

# main pyrevit lib folders
MAIN_LIB_DIR = op.join(HOME_DIR, 'pyrevitlib')
MISC_LIB_DIR = op.join(HOME_DIR, 'site-packages')

# path to pyrevit module
MODULE_DIR = op.join(MAIN_LIB_DIR, 'pyrevit')

# loader directory
LOADER_DIR = op.join(MODULE_DIR, 'loader')

# runtime directory
RUNTIME_DIR = op.join(MODULE_DIR, 'runtime')

# addin directory
ADDIN_DIR = op.join(LOADER_DIR, 'addin')

# if loader module is available means pyRevit is being executed by Revit.
import pyrevit.engine as eng
if eng.EngineVersion != 000:
    ENGINES_DIR = op.join(BIN_DIR, 'engines', eng.EngineVersion)
# otherwise it might be under test, or documentation processing.
# so let's keep the symbols but set to None (fake the symbols)
else:
    ENGINES_DIR = None

# add the framework dll path to the search paths
sys.path.append(BIN_DIR)
sys.path.append(ADDIN_DIR)
sys.path.append(ENGINES_DIR)


PYREVIT_CLI_PATH = op.join(BIN_DIR, PYREVIT_CLI_NAME)


# now we can start importing stuff
from pyrevit.compat import safe_strtype
from pyrevit.framework import Process
from pyrevit.framework import Windows
from pyrevit.framework import Forms
from pyrevit import api
from pyrevit.api import DB, UI, ApplicationServices, AdWindows

# -----------------------------------------------------------------------------
# Base Exceptions
# -----------------------------------------------------------------------------
TRACEBACK_TITLE = 'Traceback:'


# General Exceptions
class PyRevitException(Exception):
    """Common base class for all pyRevit exceptions.

    Parameters args and message are derived from Exception class.
    """

    @property
    def msg(self):
        """Return exception message."""
        if self.args:
            return self.args[0] #pylint: disable=E1136
        else:
            return ''

    def __repr__(self):
        return str(self)

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
    """Common base class for all pyRevit io-related exceptions."""


class PyRevitCPythonNotSupported(PyRevitException):
    """Common base class for all pyRevit io-related exceptions."""
    def __init__(self, feature_name):
        super(PyRevitCPythonNotSupported, self).__init__()
        self.feature_name = feature_name

    def __str__(self):
        return self.msg

    @property
    def msg(self):
        """Return exception message."""
        return '\"{}\" is not currently supported under CPython' \
                .format(self.feature_name)


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
        >>> hostapp = _HostApplication()
        >>> hostapp.is_newer_than(2017)
    """

    def __init__(self):
        self._postable_cmds = []

    @property
    def uiapp(self):
        """Return UIApplication provided to the running command."""
        if isinstance(__revit__, UI.UIApplication):  #pylint: disable=undefined-variable
            return __revit__  #pylint: disable=undefined-variable

    @property
    def app(self):
        """Return Application provided to the running command."""
        if self.uiapp:
            return self.uiapp.Application
        elif isinstance(__revit__, ApplicationServices.Application):  #pylint: disable=undefined-variable
            return __revit__  #pylint: disable=undefined-variable

    @property
    def addin_id(self):
        """Return active addin id."""
        return self.app.ActiveAddInId

    @property
    def has_api_context(self):
        """Determine if host application is in API context"""
        return self.app.ActiveAddInId is not None

    @property
    def uidoc(self):
        """Return active UIDocument."""
        return getattr(self.uiapp, 'ActiveUIDocument', None)

    @property
    def doc(self):
        """Return active Document."""
        return getattr(self.uidoc, 'Document', None)

    @property
    def active_view(self):
        """Return view that is active (UIDocument.ActiveView)."""
        return getattr(self.uidoc, 'ActiveView', None)

    @active_view.setter
    def active_view(self, value):
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
        if hasattr(self.app, 'SubVersionNumber'):
            return self.app.SubVersionNumber
        else:
            return '{}.0'.format(self.version)

    @property
    def version_name(self):
        """str: Return version name (e.g. 'Autodesk Revit 2018')."""
        return self.app.VersionName

    @property
    def build(self):
        """str: Return build number (e.g. '20170927_1515(x64)')."""
        if int(self.version) >= 2021:
            # uses labs module that is imported later in this code
            return labs.extract_build_from_exe(self.proc_path)
        else:
            return self.app.VersionBuild

    @property
    def serial_no(self):
        """str: Return serial number number (e.g. '569-09704828')."""
        return api.get_product_serial_number()

    @property
    def pretty_name(self):
        """str: Pretty name of the host
        (e.g. 'Autodesk Revit 2019.2 build: 20190808_0900(x64)')
        """
        host_name = self.version_name
        if self.is_newer_than(2017):
            host_name = host_name.replace(self.version, self.subversion)
        return "%s build: %s" % (host_name, self.build)

    @property
    def is_demo(self):
        """bool: Determine if product is using demo license."""
        return api.is_product_demo()

    @property
    def language(self):
        """str: Return language type (e.g. 'LanguageType.English_USA')."""
        return self.app.Language

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
    def proc_window(self):
        """``intptr``: Return handle to current process window."""
        if self.is_newer_than(2019, or_equal=True):
            return self.uiapp.MainWindowHandle
        else:
            return AdWindows.ComponentManager.ApplicationWindow

    @property
    def proc_screen(self):
        """``intptr``: Return handle to screen hosting current process."""
        return Forms.Screen.FromHandle(self.proc_window)

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

    def post_command(self, command_id):
        """Request Revit to run a command

        Args:
            command_id (str): command identifier e.g. ID_REVIT_SAVE_AS_TEMPLATE
        """
        command_id = UI.RevitCommandId.LookupCommandId(command_id)
        self.uiapp.PostCommand(command_id)



try:
    # Create an intance of host application wrapper
    # making sure __revit__ is available
    HOST_APP = _HostApplication()
except Exception:
    raise Exception('Critical Error: Host software is not supported. '
                    '(__revit__ handle is not available)')


# -----------------------------------------------------------------------------
# Wrapper to access builtin parameters set in scope by C# Script Executor
# -----------------------------------------------------------------------------
class _ExecutorParams(object):
    """Private Wrapper that provides runtime environment info."""

    @property   # read-only
    def exec_id(self):
        """Return execution unique id"""
        try:
            return __execid__
        except NameError:
            pass

    @property   # read-only
    def exec_timestamp(self):
        """Return execution timestamp"""
        try:
            return __timestamp__
        except NameError:
            pass

    @property   # read-only
    def engine_id(self):
        """Return engine id"""
        try:
            return __cachedengineid__
        except NameError:
            pass

    @property   # read-only
    def engine_ver(self):
        """str: Return PyRevitLoader.ScriptExecutor hardcoded version."""
        if eng.ScriptExecutor:
            return eng.ScriptExecutor.EngineVersion

    @property  # read-only
    def cached_engine(self):
        """bool: Check whether pyrevit is running on a cached engine."""
        try:
            return __cachedengine__
        except NameError:
            return False

    @property  # read-only
    def first_load(self):
        """bool: Check whether pyrevit is not running in pyrevit command."""
        # if no output window is set by the executor, it means that pyRevit
        # is loading at Revit startup (not reloading)
        return True if self.window_handle is None else False

    @property   # read-only
    def script_runtime(self):
        """``PyRevitLabs.PyRevit.Runtime.ScriptRuntime``: Return command."""
        try:
            return __scriptruntime__
        except NameError:
            return None

    @property   # read-only
    def output_stream(self):
        """Return ScriptIO"""
        if self.script_runtime:
            return self.script_runtime.OutputStream

    @property   # read-only
    def script_data(self):
        """Return ScriptRuntime.ScriptData"""
        if self.script_runtime:
            return self.script_runtime.ScriptData

    @property   # read-only
    def script_runtime_cfgs(self):
        """Return ScriptRuntime.ScriptRuntimeConfigs"""
        if self.script_runtime:
            return self.script_runtime.ScriptRuntimeConfigs

    @property   # read-only
    def engine_cfgs(self):
        """Return ScriptRuntime.ScriptRuntimeConfigs"""
        if self.script_runtime:
            return self.script_runtime.EngineConfigs

    @property
    def command_mode(self):
        """bool: Check if pyrevit is running in pyrevit command context."""
        return self.script_runtime is not None

    @property
    def event_sender(self):
        """``Object``: Return event sender object."""
        if self.script_runtime_cfgs:
            return self.script_runtime_cfgs.EventSender

    @property
    def event_args(self):
        """``DB.RevitAPIEventArgs``: Return event arguments object."""
        if self.script_runtime_cfgs:
            return self.script_runtime_cfgs.EventArgs

    @property
    def event_doc(self):
        """``DB.Document``: Return document set in event args if available."""
        if self.event_args:
            if hasattr(self.event_args, 'Document'):
                return getattr(self.event_args, 'Document')
            elif hasattr(self.event_args, 'ActiveDocument'):
                return getattr(self.event_args, 'ActiveDocument')
            elif hasattr(self.event_args, 'CurrentDocument'):
                return getattr(self.event_args, 'CurrentDocument')
            elif hasattr(self.event_args, 'GetDocument'):
                return self.event_args.GetDocument()

    @property   # read-only
    def needs_refreshed_engine(self):
        """bool: Check if command needs a newly refreshed IronPython engine."""
        if self.script_runtime_cfgs:
            return self.script_runtime_cfgs.RefreshEngine
        else:
            return False

    @property   # read-only
    def debug_mode(self):
        """bool: Check if command is in debug mode."""
        if self.script_runtime_cfgs:
            return self.script_runtime_cfgs.DebugMode
        else:
            return False

    @property   # read-only
    def config_mode(self):
        """bool: Check if command is in config mode."""
        if self.script_runtime_cfgs:
            return self.script_runtime_cfgs.ConfigMode
        else:
            return False

    @property   # read-only
    def executed_from_ui(self):
        """bool: Check if command was executed from ui."""
        if self.script_runtime_cfgs:
            return self.script_runtime_cfgs.ExecutedFromUI
        else:
            return False

    @property   # read-only
    def needs_clean_engine(self):
        """bool: Check if command needs a clean IronPython engine."""
        if self.engine_cfgs:
            return self.engine_cfgs.CleanEngine
        else:
            return False

    @property   # read-only
    def needs_fullframe_engine(self):
        """bool: Check if command needs a full-frame IronPython engine."""
        if self.engine_cfgs:
            return self.engine_cfgs.FullFrameEngine
        else:
            return False

    @property   # read-only
    def needs_persistent_engine(self):
        """bool: Check if command needs a persistent IronPython engine."""
        if self.engine_cfgs:
            return self.engine_cfgs.PersistentEngine
        else:
            return False

    @property   # read
    def window_handle(self):
        """``PyRevitLabs.PyRevit.Runtime.ScriptConsole``:
                Return output window. handle
        """
        if self.script_runtime:
            return self.script_runtime.OutputWindow

    @property
    def command_data(self):
        """``ExternalCommandData``: Return current command data."""
        if self.script_runtime_cfgs:
            return self.script_runtime_cfgs.CommandData

    @property
    def command_elements(self):
        """``DB.ElementSet``: Return elements passed to by Revit."""
        if self.script_runtime_cfgs:
            return self.script_runtime_cfgs.SelectedElements

    @property   # read-only
    def command_path(self):
        """str: Return current command path."""
        if '__commandpath__' in __builtins__ \
                and __builtins__['__commandpath__']:
            return __builtins__['__commandpath__']
        elif self.script_runtime:
            return op.dirname(self.script_runtime.ScriptData.ScriptPath)

    @property   # read-only
    def command_config_path(self):
        """str: Return current command config script path."""
        if '__configcommandpath__' in __builtins__ \
                and __builtins__['__configcommandpath__']:
            return __builtins__['__configcommandpath__']
        elif self.script_runtime:
            return op.dirname(self.script_runtime.ScriptData.ConfigScriptPath)

    @property   # read-only
    def command_name(self):
        """str: Return current command name."""
        if '__commandname__' in __builtins__ \
                and __builtins__['__commandname__']:
            return __builtins__['__commandname__']
        elif self.script_runtime:
            return self.script_runtime.ScriptData.CommandName

    @property   # read-only
    def command_bundle(self):
        """str: Return current command bundle name."""
        if '__commandbundle__' in __builtins__ \
                and __builtins__['__commandbundle__']:
            return __builtins__['__commandbundle__']
        elif self.script_runtime:
            return self.script_runtime.ScriptData.CommandBundle

    @property   # read-only
    def command_extension(self):
        """str: Return current command extension name."""
        if '__commandextension__' in __builtins__ \
                and __builtins__['__commandextension__']:
            return __builtins__['__commandextension__']
        elif self.script_runtime:
            return self.script_runtime.ScriptData.CommandExtension

    @property   # read-only
    def command_uniqueid(self):
        """str: Return current command unique id."""
        if '__commanduniqueid__' in __builtins__ \
                and __builtins__['__commanduniqueid__']:
            return __builtins__['__commanduniqueid__']
        elif self.script_runtime:
            return self.script_runtime.ScriptData.CommandUniqueId

    @property   # read-only
    def command_controlid(self):
        """str: Return current command control id."""
        if '__commandcontrolid__' in __builtins__ \
                and __builtins__['__commandcontrolid__']:
            return __builtins__['__commandcontrolid__']
        elif self.script_runtime:
            return self.script_runtime.ScriptData.CommandControlId

    @property   # read-only
    def command_uibutton(self):
        """str: Return current command ui button."""
        if '__uibutton__' in __builtins__ \
                and __builtins__['__uibutton__']:
            return __builtins__['__uibutton__']

    @property
    def doc_mode(self):
        """bool: Check if pyrevit is running by doc generator."""
        try:
            return __sphinx__
        except NameError:
            return False

    @property
    def result_dict(self):
        """``Dictionary<String, String>``: Return results dict for logging."""
        if self.script_runtime:
            return self.script_runtime.GetResultsDictionary()


# create an instance of _ExecutorParams wrapping current runtime.
EXEC_PARAMS = _ExecutorParams()


# -----------------------------------------------------------------------------
# type to safely get document instance from app or event args
# -----------------------------------------------------------------------------

class _DocsGetter(object):
    """Instance to safely get document from HOST_APP instance or EXEC_PARAMS"""

    @property
    def doc(self):
        """Active document"""
        return HOST_APP.doc or EXEC_PARAMS.event_doc

    @property
    def docs(self):
        """List of active documents"""
        return HOST_APP.docs


DOCS = _DocsGetter()

# -----------------------------------------------------------------------------
# config user environment paths
# -----------------------------------------------------------------------------
# user env paths
if EXEC_PARAMS.doc_mode:
    ALLUSER_PROGRAMDATA = USER_ROAMING_DIR = USER_SYS_TEMP = USER_DESKTOP = \
    EXTENSIONS_DEFAULT_DIR = THIRDPARTY_EXTENSIONS_DEFAULT_DIR = ' '
else:
    ALLUSER_PROGRAMDATA = os.getenv('programdata')
    USER_ROAMING_DIR = os.getenv('appdata')
    USER_SYS_TEMP = os.getenv('temp')
    USER_DESKTOP = op.expandvars('%userprofile%\\desktop')

    # verify directory per issue #369
    if not USER_DESKTOP or not op.exists(USER_DESKTOP):
        USER_DESKTOP = USER_SYS_TEMP

    # default extensions directory
    EXTENSIONS_DEFAULT_DIR = op.join(HOME_DIR, 'extensions')
    THIRDPARTY_EXTENSIONS_DEFAULT_DIR = \
        op.join(USER_ROAMING_DIR, PYREVIT_ADDON_NAME, 'Extensions')

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
    for pyrvt_app_dir in [PYREVIT_APP_DIR,
                          PYREVIT_VERSION_APP_DIR,
                          THIRDPARTY_EXTENSIONS_DEFAULT_DIR]:
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
    PYREVIT_FILE_PREFIX_UNIVERSAL = '{}_'.format(PYREVIT_ADDON_NAME)
    PYREVIT_FILE_PREFIX_UNIVERSAL_REGEX = \
        r'^' + PYREVIT_ADDON_NAME + r'_(?P<fname>.+)'

    # e.g. pyRevit_2018_
    PYREVIT_FILE_PREFIX = '{}_{}_'.format(PYREVIT_ADDON_NAME,
                                          HOST_APP.version)
    PYREVIT_FILE_PREFIX_REGEX = \
        r'^' + PYREVIT_ADDON_NAME + r'_(?P<version>\d{4})_(?P<fname>.+)'

    # e.g. pyRevit_2018_14422_
    PYREVIT_FILE_PREFIX_STAMPED = '{}_{}_{}_'.format(PYREVIT_ADDON_NAME,
                                                     HOST_APP.version,
                                                     HOST_APP.proc_id)
    PYREVIT_FILE_PREFIX_STAMPED_REGEX = \
        r'^' + PYREVIT_ADDON_NAME \
        + r'_(?P<version>\d{4})_(?P<pid>\d+)_(?P<fname>.+)'

    # e.g. pyRevit_eirannejad_
    PYREVIT_FILE_PREFIX_UNIVERSAL_USER = '{}_{}_'.format(PYREVIT_ADDON_NAME,
                                                         HOST_APP.username)
    PYREVIT_FILE_PREFIX_UNIVERSAL_USER_REGEX = \
        r'^' + PYREVIT_ADDON_NAME + r'_(?P<user>.+)_(?P<fname>.+)'

    # e.g. pyRevit_2018_eirannejad_
    PYREVIT_FILE_PREFIX_USER = '{}_{}_{}_'.format(PYREVIT_ADDON_NAME,
                                                  HOST_APP.version,
                                                  HOST_APP.username)
    PYREVIT_FILE_PREFIX_USER_REGEX = \
        r'^' + PYREVIT_ADDON_NAME \
        + r'_(?P<version>\d{4})_(?P<user>.+)_(?P<fname>.+)'

    # e.g. pyRevit_2018_eirannejad_14422_
    PYREVIT_FILE_PREFIX_STAMPED_USER = '{}_{}_{}_{}_'.format(PYREVIT_ADDON_NAME,
                                                             HOST_APP.version,
                                                             HOST_APP.username,
                                                             HOST_APP.proc_id)
    PYREVIT_FILE_PREFIX_STAMPED_USER_REGEX = \
        r'^' + PYREVIT_ADDON_NAME \
        + r'_(?P<version>\d{4})_(?P<user>.+)_(?P<pid>\d+)_(?P<fname>.+)'

# -----------------------------------------------------------------------------
# config labs modules
# -----------------------------------------------------------------------------
from pyrevit import labs
