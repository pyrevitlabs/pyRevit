"""Own native modal WPF windows through composition rather than CLR subclasses.

Important:
    Python controllers never become CLR-derived types. This avoids pythonnet
    type-registration collisions on repeated commands and reloads. Reactive
    models use managed binding adapters, plain Python lists and objects reach
    WPF through the live proxies registered by ``_proxies``, and modal,
    modeless and dockable roots share the same callback lifetime rules. A
    controller is accepted wherever .NET expects a type its native root
    satisfies, such as ``Window.Owner`` (see ``PythonBinding.RegisterRoots``).
"""

import os.path as op

import clr
from pyrevit import PyRevitException
from pyrevit import framework
from pyrevit.framework import System, Windows, Uri, UriKind
from System.Windows.Markup import XamlReader, ParserContext

from .._xaml import HookedEvent, TemplateEvent, prepare_xaml
from . import _proxies  # noqa: F401
from ._binding import FORM_STATE, Reactive, binding_source, unwrap_item
from ._events import (
    _EventRegistry,
    bind_template_event,
    hook_template_events,
    is_event_attribute,
    replay_initial_state,
)
from ._shared import Disposing, apply_pane_options, same_items
from PyRevitLabs.PyRevit.Forms.Binding import PythonBinding

_root_properties = {}


class _FormState(object):
    """Lifecycle state the backend keeps for one controller.

    Stored under the single instance attribute ``FORM_STATE`` so that
    subclass attributes such as ``_events``, ``_window`` or ``_closed`` never
    collide with it.

    Attributes:
        root: The native WPF root, or None before ``initialize``.
        events (_EventRegistry): Every callback attached to native objects.
        closed (bool): Whether the native window has closed.
        pending_resources (list[str] | None): Dictionaries queued until the
            next ``load_component``; None while no load is pending.
        xaml_names (frozenset[str]): Named XAML controls, never bound.
        data_context: The Python model assigned as ``DataContext``, kept
            alive for its native binding adapter.
        preload (dict): Native root properties assigned before a root
            existed, applied by the next ``load_component`` unless the XAML
            root sets them.
    """

    __slots__ = (
        "root",
        "events",
        "closed",
        "pending_resources",
        "xaml_names",
        "data_context",
        "preload",
    )

    def __init__(self):
        self.root = None
        self.events = _EventRegistry()
        self.closed = False
        self.pending_resources = None
        self.xaml_names = frozenset()
        self.data_context = None
        self.preload = {}


def _state(target):
    state = target.__dict__.get(FORM_STATE)
    if state is None:
        state = _FormState()
        target.__dict__[FORM_STATE] = state
    return state


def _attached_state(target):
    """Return the state of a controller from any import of this module, or None."""
    if getattr(type(target), "_pyrevit_root_type", None) is None:
        return None
    return target.__dict__.get(FORM_STATE)


def _is_root_property(controller_type, name):
    root_type = controller_type._pyrevit_root_type
    key = (root_type, name)
    if key not in _root_properties:
        clr_type = clr.GetClrType(root_type)
        _root_properties[key] = any(
            prop.Name == name for prop in clr_type.GetProperties()
        )
    return _root_properties[key]


def _set_native(state, native, name, value):
    if name == "DataContext":
        state.data_context = value
        value = binding_source(value)
    setattr(native, name, value)


def _require_sta():
    if (
        System.Threading.Thread.CurrentThread.GetApartmentState()
        != System.Threading.ApartmentState.STA
    ):
        raise PyRevitException(
            "CPython forms must be created on Revit's STA UI thread."
        )


class _Root(object):
    """Forward properties to the native WPF root this controller owns.

    Assigning ``DataContext`` keeps the Python model alive as long as the
    controller, and reading it returns that Python model rather than its
    native binding adapter. A native root property assigned before the root
    exists, as ``script.load_ui`` windows may do, is applied once the XAML
    loads unless the XAML root sets it, matching IronPython's
    ``LoadComponent``.

    Invariant:
        Backend state lives only in ``_FormState`` under ``FORM_STATE``, and
        backend logic only in module functions, so subclasses may use any
        other attribute or method name.
    """

    _binding_exclude = True
    _pyrevit_root_type = None

    def __getattr__(self, name):
        state = self.__dict__.get(FORM_STATE)
        if state is not None:
            if state.root is not None:
                value = getattr(state.root, name)
                return unwrap_item(value) if name == "DataContext" else value
            if name in state.preload:
                return state.preload[name]
        raise AttributeError(name)

    def __setattr__(self, name, value):
        state = self.__dict__.get(FORM_STATE)
        root = None if state is None else state.root
        if name.startswith("_"):
            object.__setattr__(self, name, value)
        elif root is not None and hasattr(root, name):
            _set_native(state, root, name, value)
        elif root is None and _is_root_property(type(self), name):
            _state(self).preload[name] = value
        else:
            object.__setattr__(self, name, value)


def _release(state):
    state.events.release()


def _close(state):
    window = state.root
    if window is None:
        return
    if not state.closed:
        window.Close()
    if not state.closed and window.IsLoaded:
        return
    _release(state)


class Window(_Root):
    """Own a native ``System.Windows.Window`` loaded from XAML."""

    _binding_exclude = True
    _pyrevit_root_type = Windows.Window

    def Show(self):
        """Show the native window without creating a nested modal dispatcher."""
        _state(self).root.Show()

    def ShowDialog(self):
        """Run the modal dialog and release its Python callbacks once it closes.

        An error raised by a callback while the dialog runs leaves
        ``ShowDialog`` as it does under IronPython; a window WPF leaves open
        then keeps its callbacks until it closes.
        """
        state = _state(self)
        window = state.root
        try:
            return window.ShowDialog()
        finally:
            if state.closed or not window.IsVisible:
                _release(state)

    def Close(self):
        """Close the native root and release callbacks, even before it is shown.

        A ``Closing`` handler that cancels the close leaves the window open
        with every callback still attached, so it keeps working.
        """
        _close(_state(self))


class Panel(_Root):
    """Own a native ``System.Windows.Controls.Page`` hosted by a Revit pane."""

    _binding_exclude = True
    _pyrevit_root_type = framework.Controls.Page


def _root_type_of(controller_type):
    root_type = getattr(controller_type, "_pyrevit_root_type", None)
    return None if root_type is None else clr.GetClrType(root_type)


def _root_of(controller):
    state = _attached_state(controller)
    return None if state is None else state.root


PythonBinding.RegisterRoots(_root_type_of, _root_of)


def initialize(target):
    """Prepare the controller's native root for the next ``load_component``.

    The native root is created once, on the calling STA UI thread; later calls
    keep it and its callbacks. Every call starts an empty queue of resource
    dictionaries that ``load_component`` merges into the markup.
    """
    state = _state(target)
    if state.root is None:
        _require_sta()
        state.root = type(target)._pyrevit_root_type()
        state.closed = False
    state.pending_resources = []


def unwrap(target):
    """Return a native root for WPF APIs that cannot consume Python controllers.

    Controllers created by an earlier import of this module, such as a
    modeless window kept across a reload, are unwrapped too.
    """
    state = _attached_state(target)
    if state is None or state.root is None:
        return target
    return state.root


def dispose(target):
    """Release callbacks and host subscriptions after failed initialization."""
    state = _attached_state(target)
    if state is None:
        return
    if isinstance(state.root, Windows.Window):
        _close(state)
    else:
        _release(state)


def disposing(target):
    """Return a context manager that disposes ``target`` if its body raises."""
    return Disposing(target, dispose)


def on_release(target, detach):
    """Run ``detach()`` when the form releases its callbacks.

    That happens when a window closes, when ``ShowDialog`` returns with the
    window closed, and when a form is disposed after a failed construction.
    """
    _state(target).events.on_release(detach)


def queue_resource(target, path):
    """Queue a dictionary to merge into markup that has not loaded yet.

    Returns:
        bool: False once the XAML has loaded; the caller then merges the
            dictionary into the live resources itself.
    """
    if not isinstance(target, _Root):
        return False
    pending = _state(target).pending_resources
    if pending is None:
        return False
    pending.append(path)
    return True


def set_data_context(control, model):
    """Bind ``model`` to a form or a child control through a managed adapter."""
    if isinstance(control, _Root):
        control.DataContext = model
    else:
        control.DataContext = binding_source(model)


def items_source(values):
    """Expose Python values through a managed collection understood by WPF."""
    return framework.to_clr_list(System.Object, values)


def list_source(values):
    """Return a managed snapshot of list models for an ``ItemsSource``.

    Each value is exposed through its binding adapter, so WPF sees two-way
    properties while ``items_of`` still returns the original Python objects.
    """
    return items_source([binding_source(value) for value in values])


def items_of(selector):
    """Return the Python items listed by ``selector``, in order, as a new list."""
    return [unwrap_item(item) for item in selector.ItemsSource or []]


def selected_items_of(selector):
    """Return the Python items selected in ``selector`` as a new list."""
    return [unwrap_item(item) for item in selector.SelectedItems]


def selected_item_of(selector):
    """Return the Python item selected in ``selector``, or None."""
    return unwrap_item(selector.SelectedItem)


def data_context_of(element):
    """Return the Python model behind an element's ``DataContext``."""
    return unwrap_item(element.DataContext)


def rebind_if_changed(control, items):
    """Re-list ``items`` on ``control`` if they differ from what it lists."""
    if not same_items(items, items_of(control)):
        control.ItemsSource = list_source(items)


def show_prompt(target):
    """Show an overlay whose enclosing command owns its complete lifetime."""
    _state(target).root.Show()


def make_pane_provider(panel, default_visible):
    """Build the Revit pane provider that hosts a CPython page's native root.

    The provider is a managed type so Revit never calls back into a Python
    implementation of ``IDockablePaneProvider``.
    """
    from pyrevit.runtime.types import DockablePaneProvider

    provider = DockablePaneProvider(unwrap(panel), default_visible)
    apply_pane_options(panel, provider)
    return provider


def bind_event(target, event_name, handler):
    """Retain native event callbacks until close, then detach them together."""
    _state(target).events.bind(unwrap(target), event_name, handler)


def bind_control_event(target, control, event_name, handler):
    """Keep dynamically created control callbacks within the window lifetime."""
    _state(target).events.bind(control, event_name, handler)


def _find_name(native, name, resource_names):
    if name not in resource_names:
        return native.FindName(name)
    owner_name, key = resource_names[name]
    if owner_name is None:
        owner = native
    else:
        owner = _find_name(native, owner_name, resource_names)
    resources = getattr(owner, "Resources", None)
    if resources is None or not resources.Contains(key):
        return None
    resource = resources[key]
    if not isinstance(resource, Windows.DependencyObject):
        return None
    if getattr(resource, "Name", None) == name:
        return resource
    return Windows.LogicalTreeHelper.FindLogicalNode(resource, name)


def _read_source(source):
    if isinstance(source, str):
        with open(source, encoding="utf-8-sig") as stream:
            return stream.read(), Uri(op.abspath(source), UriKind.Absolute)
    return source.ReadToEnd(), None


def _load_markup(markup, base_uri):
    stream = System.IO.MemoryStream(System.Text.Encoding.UTF8.GetBytes(markup))
    context = ParserContext()
    if base_uri is not None:
        context.BaseUri = base_uri
    try:
        return XamlReader.Load(stream, context)
    finally:
        stream.Dispose()


def _resource_sources(previous, pending):
    """Return dictionary URIs to merge into the markup, once each, in order."""
    sources = []
    merged = [str(item.Source) for item in previous.Resources.MergedDictionaries]
    queued = [str(Uri(path, UriKind.Absolute)) for path in pending]
    for source_uri in merged + queued:
        if source_uri not in sources:
            sources.append(source_uri)
    return sources


def _adopt_host_state(native, previous):
    """Carry resources and root colors set on the temporary owner to ``native``."""
    resources = previous.Resources
    for key in resources.Keys:
        if not native.Resources.Contains(key):
            native.Resources[key] = resources[key]
    for name in ("Background", "Foreground"):
        prop = getattr(framework.Controls.Control, name + "Property")
        if native.ReadLocalValue(prop) == Windows.DependencyProperty.UnsetValue:
            setattr(native, name, getattr(previous, name))


def _require_root_type(target, native):
    root_type = type(target)._pyrevit_root_type
    if not isinstance(native, root_type):
        raise PyRevitException(
            "CPython forms require a {} XAML root for {}.".format(
                root_type.__name__, type(target).__name__
            )
        )


def _swap_root(target, state, native, previous):
    """Make ``native`` the controller's root, carrying over the host state."""
    _require_root_type(target, native)
    _adopt_host_state(native, previous)
    state.root = native
    if isinstance(previous, Windows.Window):
        previous.Close()
        state.closed = False


def _apply_preload(state, native, root_properties):
    """Apply root properties set before the root existed, unless XAML sets them."""
    preload, state.preload = state.preload, {}
    for name, value in preload.items():
        if name not in root_properties:
            _set_native(state, native, name, value)


def _attach_closed(state, native):
    def closed(sender, args):
        if System.Object.ReferenceEquals(sender, state.root):
            state.closed = True
            _release(state)

    state.events.bind(native, "Closed", closed, guarded=False)


def _attach_xaml(target, state, native, prepared):
    """Expose named controls and attach deferred handlers.

    Returns:
        list[tuple]: (control, event name, callback) for handlers whose
            initial state must be replayed.
    """
    for name in prepared.names:
        control = _find_name(native, name, prepared.resource_names)
        if control is None:
            raise PyRevitException("CPython XAML name was not found: {}".format(name))
        object.__setattr__(target, name, control)
    state.xaml_names = frozenset(prepared.names)
    registry = state.events
    replays = []
    for event in prepared.events:
        if isinstance(event, HookedEvent):
            continue
        handler = getattr(target, event.handler)
        if isinstance(event, TemplateEvent):
            bind_template_event(
                registry, native, event.tag, event.uid, event.event, handler
            )
            continue
        control = getattr(target, event.name)
        callback = registry.bind(control, event.event, handler)
        if event.replay:
            replays.append((control, event.event, callback))
    if isinstance(native, Windows.Window):
        _attach_closed(state, native)
    return replays


def _hook_events(target, registry, events):
    """Register handlers of popup template elements before their markup loads.

    Returns:
        list[callable]: Undo functions for a load that fails.
    """
    handlers = {}
    for event in events:
        if isinstance(event, HookedEvent):
            handlers.setdefault(event.key, []).append(
                (event.event, getattr(target, event.handler))
            )
    return [
        hook_template_events(registry, key, pairs) for key, pairs in handlers.items()
    ]


def load_component(target, source):
    """Load a native root, resolve names, then attach retained Python handlers.

    Resource dictionaries are present during parsing so StaticResource lookup
    has the same ordering as the IronPython loader. Dictionaries queued with
    ``queue_resource`` are merged into the markup instead of the temporary
    owner, so each one, such as Theme.xaml, is parsed only once. Failures
    detach any event handlers already installed and do not subscribe to
    host-wide events.

    Root properties assigned to the controller before its root existed are
    applied after parsing unless the XAML root sets them.

    Note:
        Handlers attach after parsing, so events the parser raised are lost,
        except ``Checked`` and ``SelectionChanged`` where IronPython would
        have delivered them (see ``_xaml.NamedEvent``).
    """
    markup, base_uri = _read_source(source)
    if not isinstance(target, _Root):
        return _load_markup(markup, base_uri)
    state = _state(target)
    previous = state.root
    pending, state.pending_resources = state.pending_resources or [], None
    host_keys = [str(key) for key in previous.Resources.Keys if isinstance(key, str)]
    prepared = prepare_xaml(
        markup,
        _resource_sources(previous, pending),
        is_event=is_event_attribute,
        dynamic_keys=set(host_keys),
    )
    undo_hooks = _hook_events(target, state.events, prepared.events)
    try:
        native = _load_markup(prepared.markup, base_uri)
        _swap_root(target, state, native, previous)
    except Exception:
        for undo in undo_hooks:
            undo()
        raise
    _apply_preload(state, native, prepared.root_properties)
    try:
        replays = _attach_xaml(target, state, native, prepared)
    except Exception:
        _release(state)
        raise
    for control, event_name, callback in replays:
        replay_initial_state(control, event_name, callback)
    return native
