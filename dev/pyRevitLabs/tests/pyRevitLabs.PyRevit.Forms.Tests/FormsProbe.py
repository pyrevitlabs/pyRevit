"""Use real WPF/pythonnet with only the Revit-specific dependencies replaced.

Runs in its own STA test process because the interpreter and WPF dispatcher
are process-scoped. The production forms facade and modules are imported intact.
"""

import datetime
import os
import sys
import types
import uuid

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
        super().__init__(feature)


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


theme_changed = _HostEvent()


host = module(
    "pyrevit",
    __path__=[fixture_root],
    HOST_APP=types.SimpleNamespace(
        is_newer_than=lambda *args: True,
        uiapp=types.SimpleNamespace(ThemeChanged=theme_changed),
    ),
    EXEC_PARAMS=types.SimpleNamespace(
        command_path=fixture_root, command_name="Forms probe"
    ),
    BIN_DIR=fixture_root,
    PyRevitException=RuntimeError,
    PyRevitCPythonNotSupported=Unsupported,
)
module("pyrevit.compat", IRONPY=False)
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
    to_clr_list=to_clr_list,
    get_current_thread_id=lambda: System.Environment.CurrentManagedThreadId,
)
module("pyrevit.coreutils", __path__=[], new_uuid=lambda: str(uuid.uuid4()))
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
module("pyrevit.revit", ui=types.SimpleNamespace(resolve_icon_file=lambda *args: None))
module("pyrevit.versionmgr")
module("pyrevit.UI")

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

dialog = make_dialog(value_type="string")
try:
    dialog.Show()
except Unsupported as error:
    assert error.feature_name == "pyrevit.forms.WPFWindow.Show"
else:
    raise AssertionError("Modeless use is outside the supported tier")
assert not theme_changed.handlers

for name in forms.__all__:
    assert getattr(forms, name) is not None

try:
    make_dialog(value_type="dropdown")
except Unsupported as error:
    assert error.feature_name == "pyrevit.forms.GetValueWindow.dropdown"
else:
    raise AssertionError("Unported input modes must retain actionable errors")

try:
    forms.SelectFromList.show([])
except Unsupported as error:
    assert error.feature_name == "pyrevit.forms.SelectFromList.show"
else:
    raise AssertionError("Unported dialogs must retain actionable errors")

print("CPython WPF forms probe passed")
