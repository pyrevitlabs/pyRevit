"""Preserve IronPython's native WPF inheritance and DynamicXamlReader behavior."""

from pyrevit.framework import Windows, wpf

Window = Windows.Window


def initialize(target):
    """Keep the CLR-created IronPython window instance as the XAML root."""


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


import pyevent
from pyrevit.framework import ComponentModel


class Reactive(ComponentModel.INotifyPropertyChanged):
    """WPF property updator base mixin."""

    __namespace__ = "pyrevit.forms.backends._ipy"

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
