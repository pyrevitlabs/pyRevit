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
    assert dialog._events.is_released
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
assert dialog._events.is_released
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
assert dialog._events.is_released
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
assert dialog._events.is_released
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
environment_values["MODELESS_FORMS_PROBE"] = types.SimpleNamespace(
    _window=_backend.unwrap(dialog)
)
assert forms.activate_open_window("MODELESS_FORMS_PROBE")
environment_values["MODELESS_FORMS_PROBE"] = dialog
timer.Start()
Threading.Dispatcher.PushFrame(frame)
timer.Tick -= close_modeless
assert dialog.was_closed
assert dialog._events.is_released
assert not theme_changed.handlers
assert not forms.activate_open_window("MODELESS_FORMS_PROBE")

guarded = ModelessWindow()
allow_close = []


def keep_open(sender, args):
    """Cancel closing until the probe allows it."""
    args.Cancel = not allow_close


_backend.bind_event(guarded, "Closing", keep_open)
guarded.Show()
guarded.Close()
assert guarded.IsVisible
assert not guarded._events.is_released
allow_close.append(True)
guarded.Close()
assert not guarded.IsVisible
assert guarded._events.is_released
assert guarded.was_closed

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
provider = _DockablePane.registered[ProbePanel.panel_id][1]
assert provider.framework_element is _backend.unwrap(registered_panel)
assert not provider.visible_by_default
pane = forms.get_dockable_panel(ProbePanel)
assert pane is forms.get_dockable_panel(ProbePanel.panel_id)
uiapp = host.HOST_APP.uiapp
forms.open_dockable_panel(ProbePanel)
forms.open_dockable_panel(ProbePanel)
assert not pane.is_visible
assert len(uiapp.Idling.handlers) == 1
forms.close_dockable_panel(ProbePanel)
uiapp.raise_idling()
assert not uiapp.Idling.handlers
assert not pane.is_visible
forms.open_dockable_panel(ProbePanel)
uiapp.raise_idling()
assert not pane.is_visible
_DockablePane.created.update(_DockablePane.registered)
uiapp.raise_idling()
assert pane.is_visible
assert not uiapp.Idling.handlers
pane.Hide()
_DockablePane.created.clear()
uiapp.ActiveUIDocument = object()
pane_show = sys.modules["pyrevit.forms._pane_show"]
pane_show._PENDING_SHOW_TIMEOUT_SECONDS = 0
forms.open_dockable_panel(ProbePanel)
uiapp.raise_idling()
assert not uiapp.Idling.handlers
assert not pane.is_visible
pane_show._PENDING_SHOW_TIMEOUT_SECONDS = 60
uiapp.ActiveUIDocument = None
_DockablePane.created.update(_DockablePane.registered)
forms.open_dockable_panel(ProbePanel)
assert pane.is_visible
forms.close_dockable_panel(ProbePanel.panel_id)
assert not pane.is_visible
forms.toggle_dockable_panel(ProbePanel, True)
assert pane.is_visible

from pyrevit.forms.backends._binding import binding_source, unwrap_item


class ChildModel(forms.Reactive):
    """Expose one bound property from a nested model."""

    def __init__(self, message):
        super(ChildModel, self).__init__()
        self._message = message

    @forms.reactive
    def message(self):
        """Text the parent's bindings read through the child."""
        return self._message

    @message.setter
    def message(self, value):
        self._message = value


class ParentModel(forms.Reactive):
    """Hold a nested model and a list of models behind one DataContext."""

    def __init__(self):
        super(ParentModel, self).__init__()
        self.child = ChildModel("first")
        self.children = [ChildModel("listed")]


def read_path(model, path):
    """Read a binding path through WPF rather than through Python."""
    text = Controls.TextBlock()
    text.DataContext = model
    expression = text.SetBinding(
        Controls.TextBlock.TextProperty, System.Windows.Data.Binding(path)
    )
    expression.UpdateTarget()
    return text.Text


parent_model = ParentModel()
bound_parent = binding_source(parent_model)
assert read_path(bound_parent, "child.message") == "first"
assert read_path(bound_parent, "children[0].message") == "listed"
parent_model.child.message = "second"
assert read_path(bound_parent, "child.message") == "second"
parent_values = System.Collections.Generic.IDictionary[System.String, System.Object](
    bound_parent
)
assert unwrap_item(parent_values["child"]) is parent_model.child
assert unwrap_item(list(parent_values["children"])[0]) is parent_model.children[0]

logged_errors = []
logger.error = lambda *args: logged_errors.append(args)


def fail_panel_callback(sender, args):
    """Raise from a dockable-page callback that no command owns."""
    raise ValueError("panel callback failure")


_backend.bind_control_event(panel, panel.label, "MouseDown", fail_panel_callback)
mouse_down = Input.MouseButtonEventArgs(
    Input.Mouse.PrimaryDevice, 0, Input.MouseButton.Left
)
mouse_down.RoutedEvent = Input.Mouse.MouseDownEvent
panel.label.RaiseEvent(mouse_down)
panel.label.RaiseEvent(mouse_down)
assert len(logged_errors) == 2
assert "panel callback failure" in logged_errors[0][1]
assert panel._events.error is None


def exit_panel_callback(sender, args):
    """Raise a BaseException from a callback no command owns."""
    raise SystemExit("panel callback exit")


_backend.bind_control_event(panel, panel.label, "MouseUp", exit_panel_callback)
mouse_up = Input.MouseButtonEventArgs(
    Input.Mouse.PrimaryDevice, 0, Input.MouseButton.Left
)
mouse_up.RoutedEvent = Input.Mouse.MouseUpEvent
panel.label.RaiseEvent(mouse_up)
assert len(logged_errors) == 3
assert "panel callback exit" in logged_errors[2][1]

constructed = []


class CountingPanel(ProbePanel):
    """Count page construction to prove duplicates are refused early."""

    def __init__(self):
        constructed.append(True)
        ProbePanel.__init__(self)


try:
    forms.register_dockable_panel(CountingPanel)
    raise AssertionError("duplicate dockable registration was accepted")
except RuntimeError as error:
    assert "already registered" in str(error)
assert not constructed
assert forms.is_registered_dockable_panel(registered_panel)

edited = ChildModel("before")
editor = Controls.TextBox()
forms.set_data_context(editor, edited)
editor.SetBinding(Controls.TextBox.TextProperty, System.Windows.Data.Binding("message"))
expression = editor.GetBindingExpression(Controls.TextBox.TextProperty)
expression.UpdateTarget()
assert editor.Text == "before"
editor.Text = "after"
expression.UpdateSource()
assert edited.message == "after"

xaml_namespaces = (
    'xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation" '
    'xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"'
)


class DirectTemplateEventWindow(forms.WPFWindow):
    """Declare a direct routed event inside a template."""

    def __init__(self):
        forms.WPFWindow.__init__(
            self,
            "<Window {}><Window.Resources><DataTemplate x:Key='row'>"
            "<TextBlock Loaded='loaded'/></DataTemplate></Window.Resources>"
            "<Grid/></Window>".format(xaml_namespaces),
            literal_string=True,
        )

    def loaded(self, sender, args):
        """Never reachable for template instances under CPython."""


try:
    DirectTemplateEventWindow()
    raise AssertionError("direct template event loaded silently")
except RuntimeError as error:
    assert "direct routed event" in str(error)


class TemplateClickWindow(forms.WPFWindow):
    """Route a left-button press declared inside an item template."""

    def __init__(self):
        forms.WPFWindow.__init__(
            self,
            "<Window {}><ItemsControl x:Name='rows'><ItemsControl.ItemTemplate>"
            "<DataTemplate><Border Width='20' Height='20' Background='Red' "
            "MouseLeftButtonDown='pressed'/></DataTemplate>"
            "</ItemsControl.ItemTemplate></ItemsControl></Window>".format(
                xaml_namespaces
            ),
            literal_string=True,
        )
        self.presses = []

    def pressed(self, sender, args):
        """Record which button reached the template element."""
        self.presses.append(str(args.ChangedButton))


clicks = TemplateClickWindow()
clicks.rows.ItemsSource = forms._backend.items_source(["row"])
clicks.Show()
clicks.UpdateLayout()


def find_border(element):
    """Return the first Border instantiated from the item template."""
    if isinstance(element, Controls.Border) and str(element.Uid).startswith(
        "_pyrevit_template_"
    ):
        return element
    for index in range(Media.VisualTreeHelper.GetChildrenCount(element)):
        found = find_border(Media.VisualTreeHelper.GetChild(element, index))
        if found is not None:
            return found
    return None


template_border = find_border(_backend.unwrap(clicks))
assert template_border is not None


def press(button):
    """Raise a real preview-then-bubble mouse press on the template element."""
    for routed_event in (Input.Mouse.PreviewMouseDownEvent, Input.Mouse.MouseDownEvent):
        args = Input.MouseButtonEventArgs(Input.Mouse.PrimaryDevice, 0, button)
        args.RoutedEvent = routed_event
        template_border.RaiseEvent(args)


press(Input.MouseButton.Right)
press(Input.MouseButton.Left)
assert clicks.presses == ["Left"]
clicks.Close()

palette_window = forms.WPFWindow(
    "<Window {}><Border x:Name='swatch' "
    "Background='{{StaticResource pyRevitWindowBackgroundBrush}}'/></Window>".format(
        xaml_namespaces
    ),
    literal_string=True,
)
assert palette_window.swatch.Background is not None
palette_window.load_xaml(
    "<Window {}><Grid/></Window>".format(xaml_namespaces), literal_string=True
)
palette_window.Show()
palette_window.Close()
assert not palette_window.IsVisible


class ReplayWindow(forms.WPFWindow):
    """Load initial check states in both attribute orders."""

    def __init__(self):
        self.seen = []
        forms.WPFWindow.__init__(
            self,
            "<Window {}><StackPanel>"
            "<RadioButton x:Name='before' GroupName='a' IsChecked='True' "
            "Checked='before_checked'/>"
            "<RadioButton x:Name='after' GroupName='b' Checked='after_checked' "
            "IsChecked='True'/>"
            "</StackPanel></Window>".format(xaml_namespaces),
            literal_string=True,
        )
        self.mode = "ready"

    def before_checked(self, sender, args):
        """Read state the subclass sets only after the base initializer."""
        self.seen.append(("before", self.mode))

    def after_checked(self, sender, args):
        """Record the replay IronPython's loader would also deliver."""
        self.seen.append(("after", getattr(self, "mode", None)))


replayed = ReplayWindow()
assert replayed.seen == [("after", None)], replayed.seen
assert replayed._events.error is None
replayed.before.IsChecked = False
replayed.before.IsChecked = True
assert replayed.seen[-1] == ("before", "ready")
replayed.Close()


class ClrNamespaceEventWindow(forms.WPFWindow):
    """Defer an event outside the fallback list on a clr-namespace element."""

    def __init__(self):
        forms.WPFWindow.__init__(
            self,
            "<Window {} xmlns:c='clr-namespace:System.Windows.Controls;"
            "assembly=PresentationFramework'><c:Button x:Name='custom' "
            "MouseMove='moved'/></Window>".format(xaml_namespaces),
            literal_string=True,
        )
        self.moves = 0

    def moved(self, sender, args):
        """Count mouse moves raised on the custom-namespace element."""
        self.moves += 1


custom_events = ClrNamespaceEventWindow()
move = Input.MouseEventArgs(Input.Mouse.PrimaryDevice, 0)
move.RoutedEvent = Input.Mouse.MouseMoveEvent
custom_events.custom.RaiseEvent(move)
assert custom_events.moves == 1
custom_events.Close()

print("CPython WPF forms probe passed")
