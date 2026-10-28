"""Preserve IronPython's native WPF inheritance and DynamicXamlReader behavior."""

from pyrevit import UI
from pyrevit.framework import Controls, Windows, wpf

from ._shared import Disposing, apply_pane_options, same_items

Window = Windows.Window
Panel = Controls.Page


def initialize(target):
    """Keep the CLR-created IronPython instance as the XAML root."""


def dispose(target):
    """Preserve the existing IronPython exception and window lifecycle."""


def disposing(target):
    """Return a context manager that disposes ``target`` if its body raises."""
    return Disposing(target, dispose)


def on_release(target, detach):
    """Run ``detach()`` when a window closes; pages have no close event."""
    if isinstance(target, Windows.Window):
        target.Closed += lambda sender, args: detach()


def queue_resource(target, path):
    """Never queue: IronPython merges dictionaries into the live root."""
    return False


def set_data_context(control, model):
    """Assign the model directly; IronPython models are CLR notifiers."""
    control.DataContext = model


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
    """Return an observable snapshot of list models for an ``ItemsSource``."""
    from pyrevit.framework import ObservableCollection
    from ..reactive import TemplateListItem

    return ObservableCollection[TemplateListItem](values)


def items_of(selector):
    """Return the live ``ItemsSource``; in-place changes show immediately."""
    return selector.ItemsSource


def selected_items_of(selector):
    """Return the selector's live ``SelectedItems``."""
    return selector.SelectedItems


def selected_item_of(selector):
    """Return the selector's ``SelectedItem``."""
    return selector.SelectedItem


def data_context_of(element):
    """Return the element's ``DataContext``."""
    return element.DataContext


def rebind_if_changed(control, items):
    """Re-list ``items`` on ``control`` if they differ from what it lists."""
    current = control.ItemsSource
    if items is current or same_items(items, current or []):
        return
    control.ItemsSource = list_source(items)


def binding_source(value):
    """Keep IronPython models, which are already CLR notification objects."""
    return value


def show_prompt(target):
    """Show a command-scoped overlay using the original window implementation."""
    target.Show()


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
        apply_pane_options(self._panel, data)


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
