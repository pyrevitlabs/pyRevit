"""Check CPython-backend internals with real WPF after HostStubs.py has run."""

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
    assert dialog._pyrevit_backend.events.is_released
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
assert dialog._pyrevit_backend.events.is_released
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
assert dialog._pyrevit_backend.events.is_released
assert not theme_changed.handlers


class FailingDialog(forms.GetValueWindow):
    """Exercise Python callback errors at the native WPF event boundary."""

    def select(self, sender, args):
        """Raise an error which must leave ShowDialog as under IronPython."""
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
assert dialog.IsVisible
assert not dialog._pyrevit_backend.events.is_released
dialog.Close()
assert dialog._pyrevit_backend.events.is_released
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
earlier_import = type(
    "EarlierImportWindow", (object,), {"_pyrevit_root_type": Windows.Window}
)()
earlier_import.__dict__["_pyrevit_backend"] = types.SimpleNamespace(
    root=_backend.unwrap(dialog)
)
environment_values["MODELESS_FORMS_PROBE"] = earlier_import
assert forms.activate_open_window("MODELESS_FORMS_PROBE")
environment_values["MODELESS_FORMS_PROBE"] = dialog
timer.Start()
Threading.Dispatcher.PushFrame(frame)
timer.Tick -= close_modeless
assert dialog.was_closed
assert dialog._pyrevit_backend.events.is_released
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
assert not guarded._pyrevit_backend.events.is_released
allow_close.append(True)
guarded.Close()
assert not guarded.IsVisible
assert guarded._pyrevit_backend.events.is_released
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
    """Raise from a dockable-page callback that Python code raised."""
    raise ValueError("panel callback failure")


_backend.bind_control_event(panel, panel.label, "MouseDown", fail_panel_callback)
mouse_down = Input.MouseButtonEventArgs(
    Input.Mouse.PrimaryDevice, 0, Input.MouseButton.Left
)
mouse_down.RoutedEvent = Input.Mouse.MouseDownEvent
for attempt in range(2):
    try:
        panel.label.RaiseEvent(mouse_down)
    except ValueError as error:
        assert str(error) == "panel callback failure"
    else:
        raise AssertionError("The Python caller of RaiseEvent must receive the error")
assert not logged_errors


def exit_panel_callback(sender, args):
    """Raise a BaseException through a Python caller."""
    raise SystemExit("panel callback exit")


_backend.bind_control_event(panel, panel.label, "MouseUp", exit_panel_callback)
mouse_up = Input.MouseButtonEventArgs(
    Input.Mouse.PrimaryDevice, 0, Input.MouseButton.Left
)
mouse_up.RoutedEvent = Input.Mouse.MouseUpEvent
try:
    panel.label.RaiseEvent(mouse_up)
except SystemExit as error:
    assert str(error) == "panel callback exit"
else:
    raise AssertionError("SystemExit must reach the Python caller of RaiseEvent")
assert not logged_errors

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


class TemplateMenuWindow(forms.WPFWindow):
    """Declare a MenuItem Click inside a DataTemplate's ContextMenu."""

    def __init__(self):
        self.clicks = []
        forms.WPFWindow.__init__(
            self,
            "<Window {}><ItemsControl x:Name='rows'><ItemsControl.ItemTemplate>"
            "<DataTemplate><TextBlock Text='{{Binding}}'><TextBlock.ContextMenu>"
            "<ContextMenu><MenuItem Header='Do' Click='clicked'/></ContextMenu>"
            "</TextBlock.ContextMenu></TextBlock></DataTemplate>"
            "</ItemsControl.ItemTemplate></ItemsControl></Window>".format(
                xaml_namespaces
            ),
            literal_string=True,
        )

    def clicked(self, sender, args):
        """Record the clicked menu item of any template instance."""
        self.clicks.append(str(sender.Header))


def template_menus(element):
    """Return the ContextMenus of TextBlocks instantiated from the item template."""
    found = []
    if isinstance(element, Controls.TextBlock) and element.ContextMenu is not None:
        found.append(element.ContextMenu)
    for index in range(Media.VisualTreeHelper.GetChildrenCount(element)):
        found.extend(template_menus(Media.VisualTreeHelper.GetChild(element, index)))
    return found


def click_menu_items(menus):
    """Raise Click on the first item of each menu without opening it."""
    for menu in menus:
        menu.Items[0].RaiseEvent(Windows.RoutedEventArgs(Controls.MenuItem.ClickEvent))


menu_window = TemplateMenuWindow()
menu_window.rows.ItemsSource = forms._backend.items_source(["a", "b"])
menu_window.Show()
menu_window.UpdateLayout()
row_menus = template_menus(_backend.unwrap(menu_window))
assert len(row_menus) == 2
click_menu_items(row_menus)
assert menu_window.clicks == ["Do", "Do"], menu_window.clicks
menu_window.Close()
assert menu_window._pyrevit_backend.events.is_released
click_menu_items(row_menus)
assert menu_window.clicks == ["Do", "Do"], menu_window.clicks

from pyrevit import _cpython_wpf as cpython_wpf

data_template = Windows.DataTemplate()
loaded_template = cpython_wpf.LoadComponent(
    data_template,
    StringReader(
        "<DataTemplate {}><TextBlock Text='{{Binding}}'/></DataTemplate>".format(
            xaml_namespaces
        )
    ),
)
assert System.Object.ReferenceEquals(loaded_template, data_template)
assert isinstance(data_template.LoadContent(), Controls.TextBlock)
template_path = os.path.join(fixture_root, "WpfShimTemplate.xaml")
with open(template_path, "w", encoding="utf-8") as template_file:
    template_file.write(
        "<DataTemplate {}><Border/></DataTemplate>".format(xaml_namespaces)
    )
try:
    from_path = cpython_wpf.LoadComponent(Windows.DataTemplate(), template_path)
finally:
    os.remove(template_path)
assert isinstance(from_path.LoadContent(), Controls.Border)
plain_window = Windows.Window()
cpython_wpf.LoadComponent(
    plain_window, StringReader("<Window {} Title='shim'/>".format(xaml_namespaces))
)
assert plain_window.Title == "shim"


class PythonDerivedWindow(Windows.Window):
    """A Python Window subclass, which only IronPython's loader supports."""


try:
    cpython_wpf.LoadComponent(
        PythonDerivedWindow(), StringReader("<Window {}/>".format(xaml_namespaces))
    )
    raise AssertionError("A Python-derived window loaded through the wpf shim")
except Unsupported as error:
    assert "PythonDerivedWindow" in str(error)

print("CPython WPF forms probe passed")
