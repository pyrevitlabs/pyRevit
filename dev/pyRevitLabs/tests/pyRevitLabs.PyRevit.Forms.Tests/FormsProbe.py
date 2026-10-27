"""Use real WPF/pythonnet with only the Revit-specific dependencies replaced.

Runs in its own STA test process because the interpreter and WPF dispatcher
are process-scoped. The production forms facade and modules are imported intact.
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
        self.value = str(pane_uuid)


class _DockablePane:
    registered = {}

    def __init__(self):
        self.is_visible = False

    @staticmethod
    def PaneIsRegistered(pane_id):
        return pane_id.value in _DockablePane.registered

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

    def RegisterDockablePane(self, pane_id, title, provider):
        _DockablePane.registered[pane_id.value] = (title, provider, _DockablePane())

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
module("pyrevit.UI", DockablePane=_DockablePane, DockablePaneId=_DockablePaneId)
module("pyrevit.DB")
module("pyrevit.runtime", __path__=[])
module("pyrevit.runtime.types", DockablePaneProvider=_DockablePaneProvider)

from pyrevit import forms
from pyrevit.forms import _backend

assert "pyevent" not in sys.modules
assert forms.ask_for_string.__module__ == "pyrevit.forms.dialogs"
assert forms.alert.__module__ == "pyrevit.forms.native"


def make_dialog(**kwargs):
    """Construct the production dialog without showing it."""
    return forms.GetValueWindow(None, "Probe", 400, 300, **kwargs)


for cycle in range(3):
    dialog = make_dialog(
        value_type="string", default="taken", reserved_values=["taken"]
    )
    assert len(theme_changed.handlers) == 1
    assert dialog.stringValue_tb.Text == "taken"
    assert not dialog.okayButton.IsEnabled
    dialog.stringValue_tb.Text = "available"
    assert dialog.okayButton.IsEnabled
    assert dialog.Resources["pyRevitWindowBackgroundBrush"] is not None
    assert dialog.get_locale_string("pyRevit.DefaultWindowTitle") == "User Input"
    assert _backend.unwrap(dialog).FindName("okayButton") == dialog.okayButton
    dialog.okayButton.RaiseEvent(Windows.RoutedEventArgs(Controls.Button.ClickEvent))
    assert dialog.response == "available"
    assert not dialog._event_bindings
    assert not theme_changed.handlers

dialog = make_dialog(value_type="date", default=datetime.datetime(2026, 10, 26))
dialog.select(None, None)
assert dialog.response == datetime.datetime(2026, 10, 26)

dialog = make_dialog(value_type="slider", default=25, min=0, max=100, interval=5)
dialog.select(None, None)
assert dialog.response == 25.0

dialog = make_dialog(value_type="string", default="cancel me")
dialog.Close()
assert dialog.response is None

dialog = make_dialog(value_type="string", default="modal")
timer = Threading.DispatcherTimer()
timer.Interval = System.TimeSpan.FromMilliseconds(20)


def accept(sender, args):
    """Close through the real XAML callback while ShowDialog pumps WPF."""
    timer.Stop()
    dialog.okayButton.RaiseEvent(Windows.RoutedEventArgs(Controls.Button.ClickEvent))


timer.Tick += accept
timer.Start()
dialog.ShowDialog()
timer.Tick -= accept
assert dialog.response == "modal"
assert not dialog._event_bindings
assert not theme_changed.handlers

dialog = make_dialog(value_type="string", default="escape")


def escape(sender, args):
    """Route Escape through the window's actual PreviewKeyDown subscription."""
    timer.Stop()
    native = _backend.unwrap(dialog)
    source = Windows.PresentationSource.FromVisual(native)
    event = Input.KeyEventArgs(
        Input.Keyboard.PrimaryDevice, source, 0, Input.Key.Escape
    )
    event.RoutedEvent = Input.Keyboard.PreviewKeyDownEvent
    native.RaiseEvent(event)


timer.Tick += escape
timer.Start()
dialog.ShowDialog()
timer.Tick -= escape
assert dialog.response is None
assert not dialog._event_bindings
assert not theme_changed.handlers


class FailingDialog(forms.GetValueWindow):
    """Exercise Python callback errors at the native WPF event boundary."""

    def select(self, sender, args):
        """Raise an error which must reach the caller instead of the Dispatcher."""
        raise ValueError("callback failed")


dialog = FailingDialog(None, "Error probe", 400, 300, value_type="string")
timer.Tick += accept
timer.Start()
try:
    dialog.ShowDialog()
except ValueError as error:
    assert str(error) == "callback failed"
else:
    raise AssertionError("Callback errors must be returned to the Python caller")
finally:
    timer.Stop()
    timer.Tick -= accept
assert not dialog._event_bindings
assert not theme_changed.handlers


class FailingSetup(forms.GetValueWindow):
    """Ensure a constructor error cannot retain a Revit event subscription."""

    def _setup(self, **kwargs):
        raise ValueError("setup failed")


try:
    FailingSetup(None, "Setup error", 400, 300)
except ValueError as error:
    assert str(error) == "setup failed"
else:
    raise AssertionError("Setup errors must propagate")
assert not theme_changed.handlers


class ModelessWindow(forms.WPFWindow):
    """Exercise CPython modeless ownership and callback cleanup."""

    def __init__(self):
        forms.WPFWindow.__init__(
            self,
            '<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation" '
            'xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">'
            '<StackPanel><Button x:Name="close_button"/></StackPanel></Window>',
            literal_string=True,
        )
        self.was_closed = False
        self.Closed += self.closed

    def closed(self, sender, args):
        """Record that the native window completed its lifecycle."""
        self.was_closed = True


dialog = ModelessWindow()
dispatcher = Threading.Dispatcher.CurrentDispatcher
frame = Threading.DispatcherFrame()
timer = Threading.DispatcherTimer()
timer.Interval = System.TimeSpan.FromMilliseconds(30)


def close_modeless(sender, args):
    """Close the test window and return the temporary dispatcher loop."""
    timer.Stop()
    dialog.Close()
    frame.Continue = False


timer.Tick += close_modeless
dialog.Show()
assert dialog.IsVisible
environment_values["MODELESS_FORMS_PROBE"] = dialog
assert forms.activate_open_window("MODELESS_FORMS_PROBE")
timer.Start()
Threading.Dispatcher.PushFrame(frame)
timer.Tick -= close_modeless
assert dialog.was_closed
assert not dialog._event_bindings
assert not theme_changed.handlers
assert not forms.activate_open_window("MODELESS_FORMS_PROBE")

for name in forms.__all__:
    assert getattr(forms, name) is not None


class ProbePanel(forms.WPFPanel):
    """Load a CPython dockable-page controller without a Revit pane host."""

    panel_id = "0ac6ce8e-d7ba-4d8a-b5bb-c96ceeb98fb1"
    panel_source = os.path.join(fixture_root, "PanelProbe.xaml")
    panel_title = "Panel Probe"


panel = ProbePanel()
assert isinstance(_backend.unwrap(panel), Controls.Page)
assert panel.label.Text == "Panel probe"
assert not forms.is_registered_dockable_panel(ProbePanel)
registered_panel = forms.register_dockable_panel(ProbePanel, default_visible=False)
assert isinstance(registered_panel, ProbePanel)
assert forms.is_registered_dockable_panel(ProbePanel)
provider = forms._cpy._panel_providers[ProbePanel.panel_id]
assert provider.framework_element is _backend.unwrap(registered_panel)
assert not provider.visible_by_default
pane = forms.get_dockable_panel(ProbePanel)
assert pane is forms.get_dockable_panel(ProbePanel.panel_id)
forms.open_dockable_panel(ProbePanel)
assert pane.is_visible
forms.close_dockable_panel(ProbePanel.panel_id)
assert not pane.is_visible
forms.toggle_dockable_panel(ProbePanel, True)
assert pane.is_visible

print("CPython WPF forms probe passed")
