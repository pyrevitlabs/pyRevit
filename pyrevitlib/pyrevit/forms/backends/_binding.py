"""Managed notification models for Python form controllers and list items.

WPF reads native dynamic properties while Python retains the original objects.
Weak controller references keep native event delegates from rooting closed forms.
"""

import weakref

import clr
from pyrevit.framework import System, ComponentModel, to_clr_list

try:
    clr.AddReference("System.Linq.Expressions")
except System.IO.FileNotFoundException:
    clr.AddReference("System.Core")

from System.Dynamic import ExpandoObject
from System.Collections.Generic import IDictionary


_controllers = weakref.WeakValueDictionary()
_type_properties = {}
_MISSING = object()


class _Event(object):
    def __init__(self):
        self.handlers = []

    def __iadd__(self, handler):
        self.handlers.append(handler)
        return self

    def __isub__(self, handler):
        self.handlers.remove(handler)
        return self


class Reactive(object):
    """Keep Python property notifications connected to a managed binding model."""

    @property
    def PropertyChanged(self):
        """Provide per-controller subscriptions for existing Python consumers."""
        if "_property_changed" not in self.__dict__:
            self.__dict__["_property_changed"] = _Event()
        return self.__dict__["_property_changed"]

    @PropertyChanged.setter
    def PropertyChanged(self, value):
        self.__dict__["_property_changed"] = value

    def add_PropertyChanged(self, value):
        """Subscribe a Python listener to property changes."""
        self.PropertyChanged += value

    def remove_PropertyChanged(self, value):
        """Detach a previously subscribed listener."""
        self.PropertyChanged -= value

    def OnPropertyChanged(self, prop_name):
        """Refresh native values and notify existing Python listeners.

        Only ``prop_name`` is copied to the native model, matching WPF's
        per-property notification; an empty name refreshes every property.
        """
        _refresh(self, [prop_name] if prop_name else None)
        args = ComponentModel.PropertyChangedEventArgs(prop_name)
        for handler in list(self.PropertyChanged.handlers):
            handler(self, args)


def _properties_of(cls):
    names = _type_properties.get(cls)
    if names is None:
        names = frozenset(
            name for name in dir(cls) if isinstance(getattr(cls, name, None), property)
        )
        _type_properties[cls] = names
    return names


def _property_names(controller):
    names = set(controller.__dict__)
    names.update(_properties_of(type(controller)))
    wrapped = controller.__dict__.get("item")
    if wrapped is not None and hasattr(wrapped, "__dict__"):
        names.update(wrapped.__dict__)
        names.update(_properties_of(type(wrapped)))
    return [
        name for name in names if not name.startswith("_") and name != "PropertyChanged"
    ]


def _bindable(value):
    """Return a value WPF can bind: nested models and lists become managed too."""
    if isinstance(value, Reactive):
        return binding_source(value)
    if isinstance(value, (list, tuple)):
        return to_clr_list(System.Object, [_bindable(item) for item in value])
    return value


def _change_marker(value):
    return tuple(value) if isinstance(value, (list, tuple)) else value


def _unchanged(previous, marker):
    if previous is marker:
        return True
    try:
        return bool(previous == marker)
    except Exception:
        return False


def _refresh(controller, names=None):
    state = controller.__dict__
    values = state.get("_binding_values")
    if values is None or state.get("_binding_updating"):
        return
    markers = state.setdefault("_binding_markers", {})
    state["_binding_updating"] = True
    try:
        for name in names or _property_names(controller):
            try:
                value = getattr(controller, name)
            except Exception:
                continue
            if callable(value) or value is controller:
                continue
            marker = _change_marker(value)
            previous = markers.get(name, _MISSING)
            if previous is not _MISSING and _unchanged(previous, marker):
                continue
            markers[name] = marker
            values[name] = _bindable(value)
    finally:
        state["_binding_updating"] = False


def binding_source(controller):
    """Return a stable managed model with two-way property and item identity."""
    if not isinstance(controller, Reactive):
        return controller
    state = controller.__dict__
    if "_binding_model" in state:
        _refresh(controller)
        return state["_binding_model"]
    model = ExpandoObject()
    state["_binding_model"] = model
    state["_binding_values"] = IDictionary[System.String, System.Object](model)
    _controllers[model] = controller
    _refresh(controller)
    reference = weakref.ref(controller)

    def changed(sender, args):
        target = reference()
        if target is None or target.__dict__.get("_binding_updating"):
            return
        name = args.PropertyName
        prop = getattr(type(target), name, None)
        if isinstance(prop, property) and prop.fset is None:
            return
        target.__dict__["_binding_updating"] = True
        try:
            setattr(target, name, unwrap_item(target.__dict__["_binding_values"][name]))
        finally:
            target.__dict__["_binding_updating"] = False
        _refresh(target)

    notifier = ComponentModel.INotifyPropertyChanged(model)
    notifier.PropertyChanged += changed
    return model


def unwrap_item(value):
    """Recover the original Python item from a native selection or DataContext."""
    if isinstance(value, ExpandoObject):
        return _controllers.get(value, value)
    return value
