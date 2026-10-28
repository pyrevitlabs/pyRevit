"""Managed notification models for Python form controllers and list items.

WPF reads typed managed properties while Python retains the original objects.
Weak controller references keep native event delegates from rooting closed forms.

Important:
    The managed model never keeps its Python model alive. Whoever sets a model
    as a ``DataContext`` must hold a strong reference for as long as the
    binding is in use; the CPython ``Window`` and ``Panel`` controllers do
    this for their own ``DataContext``.
"""

import weakref

import clr
from pyrevit.framework import System, ComponentModel, to_clr_list

clr.AddReference("pyRevitLabs.PyRevit.Forms.Binding")
from PyRevitLabs.PyRevit.Forms.Binding import BindingModel  # noqa: E402


FORM_STATE = "_pyrevit_backend"
"""Instance attribute holding a CPython form's backend state; see ``_cpy._FormState``."""

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

    _binding_exclude = True

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
    """Return the bindable property names declared along ``cls.__mro__``.

    A class that sets ``_binding_exclude = True`` in its own body, such as
    the form base classes and shipped dialogs, contributes no properties;
    subclasses that do not set it still do.
    """
    names = _type_properties.get(cls)
    if names is None:
        found = set()
        seen = set()
        for klass in cls.__mro__:
            excluded = vars(klass).get("_binding_exclude", False)
            for name, value in vars(klass).items():
                if name in seen:
                    continue
                seen.add(name)
                if isinstance(value, property) and not excluded:
                    found.add(name)
        names = frozenset(found)
        _type_properties[cls] = names
    return names


def _public(controller, names):
    excluded = getattr(controller.__dict__.get(FORM_STATE), "xaml_names", ())
    return [
        name
        for name in names
        if not name.startswith("_")
        and name != "PropertyChanged"
        and name not in excluded
    ]


def _plain_names(controller):
    cls = type(controller)
    names = set(
        name
        for name in controller.__dict__
        if not isinstance(getattr(cls, name, None), property)
    )
    wrapped = controller.__dict__.get("item")
    if wrapped is not None and hasattr(wrapped, "__dict__"):
        names.update(wrapped.__dict__)
    return _public(controller, names)


def _own_names(controller):
    names = set(_plain_names(controller))
    names.update(_properties_of(type(controller)))
    return _public(controller, names)


def _property_names(controller):
    names = set(_own_names(controller))
    wrapped = controller.__dict__.get("item")
    if wrapped is not None and hasattr(wrapped, "__dict__"):
        names.update(_properties_of(type(wrapped)))
    return _public(controller, names)


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
    if values is None:
        return
    if state.get("_binding_updating"):
        if names is None:
            state["_binding_pending_all"] = True
        else:
            state.setdefault("_binding_pending", set()).update(names)
        return
    markers = state.setdefault("_binding_markers", {})
    state["_binding_updating"] = True
    try:
        for name in _property_names(controller) if names is None else names:
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
    """Return a stable managed model with two-way property and item identity.

    The first call copies every bindable value. Later calls for the same model
    re-copy its plain instance attributes and the properties its own class
    hierarchy declares, so computed values such as ``TemplateListItem.name``
    and ``checkable`` are current when a list is rebound. Only values that
    changed reach WPF. Properties of classes marked ``_binding_exclude``,
    such as ``pyrevit_version``, ``logger`` and ``output`` on the form base
    classes, and the form's named XAML controls are never copied.

    A two-way edit from WPF writes the edited name, then re-copies that name,
    the names its setter notified and any plain attribute the setter changed;
    it runs no other property getter.

    Warning:
        The returned model holds its Python model weakly; keep a strong
        reference to ``controller`` while the model is bound.
    """
    if not isinstance(controller, Reactive):
        return controller
    state = controller.__dict__
    if "_binding_model" in state:
        _refresh(controller, _own_names(controller))
        return state["_binding_model"]
    model = BindingModel()
    state["_binding_model"] = model
    state["_binding_values"] = model
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
        state = target.__dict__
        state["_binding_updating"] = True
        try:
            setattr(target, name, unwrap_item(state["_binding_values"][name]))
        finally:
            state["_binding_updating"] = False
        notified = state.pop("_binding_pending", set())
        notified.add(name)
        if state.pop("_binding_pending_all", False):
            _refresh(target)
            return
        _refresh(target, sorted(notified))
        _refresh(target, _plain_names(target))

    model.PropertyChanged += changed
    return model


def unwrap_item(value):
    """Recover the original Python item from a native selection or DataContext."""
    if isinstance(value, BindingModel):
        return _controllers.get(value, value)
    return value


def model_of(native):
    """Return the live Python model behind a managed binding model, or None."""
    return _controllers.get(native)
