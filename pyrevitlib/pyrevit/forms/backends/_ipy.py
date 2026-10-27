"""Preserve IronPython's native WPF inheritance and DynamicXamlReader behavior."""

from pyrevit import UI
from pyrevit.coreutils import envvars
from pyrevit.framework import Controls, Interop, System, Windows, wpf

Window = Windows.Window
Panel = Controls.Page


def initialize(target):
    """Keep the CLR-created IronPython window instance as the XAML root."""


def initialize_panel(target):
    """Keep the CLR-created IronPython page instance as the XAML root."""


def dispose(target):
    """Preserve the existing IronPython exception and window lifecycle."""


def bind_event(target, event_name, handler):
    """Attach a handler directly using IronPython's CLR event implementation."""
    event = getattr(target, event_name)
    event += handler


def bind_control_event(target, control, event_name, handler):
    """Attach dynamic control handlers through IronPython's CLR event support."""
    event = getattr(control, event_name)
    event += handler


def unwrap(target):
    """Return the native object used directly by IronPython."""
    return target


def items_source(values):
    """Keep IronPython's existing collection conversion behavior."""
    return values


def list_source(values):
    """Keep the existing observable IronPython list model."""
    from pyrevit.framework import ObservableCollection
    from ..reactive import TemplateListItem

    return ObservableCollection[TemplateListItem](values)


def binding_source(value):
    """Keep IronPython models, which are already CLR notification objects."""
    return value


def unwrap_item(value):
    """Keep native IronPython list items unchanged."""
    return value


def show_prompt(target):
    """Show a command-scoped overlay using the original window implementation."""
    target.Show()


def validate_input(value_type):
    """Keep all existing IronPython input modes available."""


def load_component(target, source):
    """Populate the existing root, names and event handlers using IronPython WPF."""
    return wpf.LoadComponent(target, source)


def make_pane_provider(panel, default_visible):
    """Wrap an IronPython page in a Python ``IDockablePaneProvider``."""
    return _PaneProvider(panel, default_visible)


class _PaneProvider(UI.IDockablePaneProvider):
    def __init__(self, panel, default_visible):
        self._panel = panel
        self._default_visible = default_visible

    def SetupDockablePane(self, data):
        data.FrameworkElement = self._panel
        data.VisibleByDefault = self._default_visible
        if self._panel.initial_state is not None:
            data.InitialState = self._panel.initial_state
        if self._panel.editor_interaction is not None:
            data.EditorInteraction = self._panel.editor_interaction
        if self._panel.contextual_help is not None:
            data.ContextualHelp = self._panel.contextual_help


def activate_open_window(envvar):
    """Bring a modeless window left open by an earlier run to the front.

    Single-instance guard for modeless tools: the tool stores its window
    under ``envvar`` with ``script.set_envvar`` when it opens it, and calls
    this on every run before creating a new one. A minimized window is
    restored before activation; a hidden one is left hidden.

    Openness is judged by the window's native handle, which WPF releases on
    close, not by ``IsLoaded``, which stays True after ``Close()``. Callers
    therefore need not clear ``envvar`` in their ``Closed`` handler.

    Args:
        envvar (str): pyRevit environment variable holding the window.

    Returns:
        (bool): True when a window already exists, meaning the caller must
            not open another. It does not promise the window is now in front:
            Windows may refuse the foreground request, and a hidden window
            stays hidden. False otherwise; a stale (closed) reference is
            cleared.

    Examples:
        ```python
        from pyrevit import forms, script

        if not forms.activate_open_window("MYTOOL_WINDOW"):
            window = MyToolWindow("MyTool.xaml")
            script.set_envvar("MYTOOL_WINDOW", window)
            window.show()
        ```
    """
    window = envvars.get_pyrevit_env_var(envvar)
    if window is None:
        return False
    try:
        is_open = Interop.WindowInteropHelper(window).Handle != System.IntPtr.Zero
    except Exception:
        is_open = False
    if not is_open:
        envvars.set_pyrevit_env_var(envvar, None)
        return False
    if window.IsVisible:
        if window.WindowState == Windows.WindowState.Minimized:
            window.WindowState = Windows.WindowState.Normal
        window.Activate()
    return True


import pyevent
from pyrevit.framework import ComponentModel


class Reactive(ComponentModel.INotifyPropertyChanged):
    """WPF property updator base mixin."""

    PropertyChanged, _propertyChangedCaller = pyevent.make_event()

    def add_PropertyChanged(self, value):
        """Called when a property is added to the object."""
        self.PropertyChanged += value

    def remove_PropertyChanged(self, value):
        """Called when a property is removed from the object."""
        self.PropertyChanged -= value

    def OnPropertyChanged(self, prop_name):
        """Called when a property is changed.

        Args:
            prop_name (str): property name
        """
        if self._propertyChangedCaller:
            args = ComponentModel.PropertyChangedEventArgs(prop_name)
            self._propertyChangedCaller(self, args)
