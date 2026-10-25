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


def unwrap(target):
    """Return the native object used directly by IronPython."""
    return target


def items_source(values):
    """Keep IronPython's existing collection conversion behavior."""
    return values


def validate_input(value_type):
    """Keep all existing IronPython input modes available."""


def load_component(target, source):
    """Populate the existing root, names and event handlers using IronPython WPF."""
    return wpf.LoadComponent(target, source)
