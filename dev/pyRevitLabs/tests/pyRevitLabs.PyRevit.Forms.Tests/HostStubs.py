"""Replace only the Revit-specific pyRevit modules so real WPF forms load.

Shared by the CPython and IronPython fixtures. Runs in its own STA test
process because the interpreter and WPF dispatcher are process-scoped. The
production forms modules are imported intact afterwards.
"""

import datetime
from io import open
import os
import sys
import types
import uuid

if not hasattr(types, "SimpleNamespace"):

    class SimpleNamespace(object):
        """Provide the Python 3.3-compatible namespace used by test doubles."""

        def __init__(self, **values):
            self.__dict__.update(values)

    types.SimpleNamespace = SimpleNamespace

sys.path.insert(0, fixture_root)

import clr

assemblies = [
    "System.Windows.Forms",
    "PresentationFramework",
    "PresentationCore",
    "WindowsBase",
    "System.Xaml",
]
for assembly in assemblies:
    clr.AddReference(assembly)

import System
from System import Windows, Uri, UriKind
from System.IO import StringReader
from System.Windows import Controls, Documents, Input, Interop, Media, Threading
from System.Windows import ResourceDictionary
from System.Windows.Media import Imaging
from System.Collections.Generic import List
from System.Collections.ObjectModel import ObservableCollection


def module(name, **values):
    """Install a focused host replacement without mocking any WPF types."""
    result = types.ModuleType(name)
    result.__dict__.update(values)
    sys.modules[name] = result
    return result


class Unsupported(Exception):
    """Match the facade's unsupported-feature contract."""

    def __init__(self, feature):
        self.feature_name = feature
        Exception.__init__(self, feature)


def to_clr_list(item_type, values):
    """Use the same Add-based conversion as pyrevit.framework."""
    result = List[item_type]()
    for value in values:
        result.Add(value)
    return result


class _HostEvent:
    def __init__(self):
        self.handlers = []

    def __iadd__(self, handler):
        self.handlers.append(handler)
        return self

    def __isub__(self, handler):
        self.handlers.remove(handler)
        return self


class _DockablePaneId:
    def __init__(self, pane_uuid):
        self.Guid = pane_uuid
        self.value = str(pane_uuid)


class _DockablePane:
    registered = {}
    created = set()

    def __init__(self):
        self.is_visible = False

    @staticmethod
    def PaneIsRegistered(pane_id):
        return pane_id.value in _DockablePane.registered

    @staticmethod
    def PaneExists(pane_id):
        return pane_id.value in _DockablePane.created

    def Show(self):
        self.is_visible = True

    def Hide(self):
        self.is_visible = False


class _DockablePaneProvider:
    def __init__(self, framework_element, visible_by_default):
        self.framework_element = framework_element
        self.visible_by_default = visible_by_default
        self.InitialState = None
        self.EditorInteraction = None
        self.ContextualHelp = None


class _UiApplication:
    def __init__(self):
        self.ThemeChanged = theme_changed
        self.Idling = _HostEvent()
        self.ActiveUIDocument = None

    def RegisterDockablePane(self, pane_id, title, provider):
        _DockablePane.registered[pane_id.value] = (title, provider, _DockablePane())

    def raise_idling(self):
        for handler in list(self.Idling.handlers):
            handler(self, None)

    def GetDockablePane(self, pane_id):
        return _DockablePane.registered[pane_id.value][2]


theme_changed = _HostEvent()


host = module(
    "pyrevit",
    __path__=[fixture_root],
    HOST_APP=types.SimpleNamespace(
        is_newer_than=lambda *args: True,
        uiapp=_UiApplication(),
    ),
    EXEC_PARAMS=types.SimpleNamespace(
        command_path=fixture_root, command_name="Forms probe"
    ),
    BIN_DIR=fixture_root,
    ROOT_BIN_DIR=fixture_root,
    DOCS=types.SimpleNamespace(docs=[]),
    PyRevitException=RuntimeError,
    PyRevitCPythonNotSupported=Unsupported,
)
module(
    "pyrevit.compat",
    IRONPY=bool(globals().get("ironpython_probe")),
    safe_strtype=str,
    get_elementid_value_func=lambda: lambda value: value.Value,
)
framework = module(
    "pyrevit.framework",
    System=System,
    Windows=Windows,
    Threading=Threading,
    Interop=Interop,
    Input=Input,
    Media=Media,
    Controls=Controls,
    Documents=Documents,
    Imaging=Imaging,
    Uri=Uri,
    UriKind=UriKind,
    ResourceDictionary=ResourceDictionary,
    StringReader=StringReader,
    Forms=System.Windows.Forms,
    CPDialogs=None,
    ComponentModel=System.ComponentModel,
    ObservableCollection=ObservableCollection,
    to_clr_list=to_clr_list,
    get_current_thread_id=lambda: System.Environment.CurrentManagedThreadId,
)
module(
    "pyrevit.coreutils",
    __path__=[],
    Guid=System.Guid,
    new_uuid=lambda: str(uuid.uuid4()),
    fuzzy_search_ratio=lambda target_string, sfilter, regex: (
        100 if sfilter.lower() in target_string.lower() else 0
    ),
)
environment_values = {}
module(
    "pyrevit.coreutils.envvars",
    get_pyrevit_env_var=lambda name: environment_values.get(name),
    set_pyrevit_env_var=lambda name, value: environment_values.__setitem__(name, value),
)
colors_module = module("pyrevit.coreutils.colors")
with open(os.path.join(fixture_root, "colors.py"), encoding="utf-8") as source:
    exec(compile(source.read(), "colors.py", "exec"), colors_module.__dict__)
logger = types.SimpleNamespace(debug=lambda *args: None, warning=lambda *args: None)
module("pyrevit.coreutils.logger", get_logger=lambda name: logger)
module(
    "pyrevit.api",
    AdWindows=types.SimpleNamespace(
        ComponentManager=types.SimpleNamespace(ApplicationWindow=System.IntPtr.Zero)
    ),
)
module("pyrevit.labs", Common=types.SimpleNamespace())
module("pyrevit.userconfig", user_config=types.SimpleNamespace(user_locale="en_us"))
module(
    "pyrevit.revit",
    ui=types.SimpleNamespace(
        resolve_icon_file=lambda *args: None,
        get_window_rectangle=lambda: System.Drawing.Rectangle(0, 0, 1920, 1080),
        get_mainwindow=lambda: None,
    ),
)
host.HOST_APP.proc_screen_workarea = System.Drawing.Rectangle(0, 0, 1920, 1080)
host.HOST_APP.proc_screen_scalefactor = 1.0
sys.modules["pyrevit.coreutils"].SafeDict = dict
module(
    "pyrevit.versionmgr",
    get_pyrevit_version=lambda: types.SimpleNamespace(get_formatted=lambda: "test"),
)
module(
    "pyrevit.UI",
    DockablePane=_DockablePane,
    DockablePaneId=_DockablePaneId,
    IDockablePaneProvider=object,
)
module("pyrevit.DB")


class _ScriptConfig(object):
    def __init__(self):
        self.values = {}

    def get_option(self, name, default=None):
        return self.values.get(name, default)

    def set_option(self, name, value):
        self.values[name] = value


script_configs = {}
script_saves = []
host.script = module(
    "pyrevit.script",
    get_config=lambda section=None: script_configs.setdefault(section, _ScriptConfig()),
    save_config=lambda: script_saves.append(True),
    reset_config=lambda section=None: script_configs.pop(section, None),
)
host.op = os.path
framework.Color = Media.Color
framework.SolidColorBrush = Media.SolidColorBrush
sys.modules["pyrevit.coreutils"].configparser = module(
    "pyrevit.coreutils.configparser", open_config_file=lambda path: None
)
sys.modules["pyrevit.coreutils"].appdata = module(
    "pyrevit.coreutils.appdata", get_universal_data_file=lambda **kwargs: None
)
module("pyrevit.runtime", __path__=[])
module("pyrevit.runtime.types", DockablePaneProvider=_DockablePaneProvider)
