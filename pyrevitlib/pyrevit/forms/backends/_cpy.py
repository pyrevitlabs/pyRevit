"""Own native modal WPF windows through composition rather than CLR subclasses.

Important:
    Python controllers never become CLR-derived types. This avoids pythonnet
    type-registration collisions on repeated commands and reloads. Reactive
    models use managed binding adapters, and modal, modeless and dockable roots
    share the same callback lifetime rules.
"""

import os.path as op

from pyrevit import PyRevitException
from pyrevit import framework
from pyrevit.framework import System, Windows, Uri, UriKind
from System.Windows.Markup import XamlReader, ParserContext

from .._xaml import TemplateEvent, prepare_xaml
from ._binding import Reactive, binding_source, unwrap_item
from ._events import (
    _EventRegistry,
    bind_template_event,
    is_event_attribute,
    replay_initial_state,
)
from ._shared import Disposing, apply_pane_options, same_items


def _forward_get(native, name):
    if native is None:
        raise AttributeError(name)
    value = getattr(native, name)
    if name == "DataContext":
        return unwrap_item(value)
    return value


def _forward_set(target, native, name, value):
    if not name.startswith("_") and native is not None and hasattr(native, name):
        if name == "DataContext":
            object.__setattr__(target, "_data_context", value)
            value = binding_source(value)
        setattr(native, name, value)
    else:
        object.__setattr__(target, name, value)


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
    native binding adapter.

    Invariant:
        Only the controller writes its lifecycle state: the native root, the
        callback registry (``_events``), the pending resource dictionaries and
        the loaded XAML names. Backend functions call its methods.
    """

    _binding_exclude = True
    _root_slot = None
    _root_type = None

    def __getattr__(self, name):
        return _forward_get(self.__dict__.get(self._root_slot), name)

    def __setattr__(self, name, value):
        _forward_set(self, self.__dict__.get(self._root_slot), name, value)

    def _root(self):
        return self.__dict__.get(self._root_slot)

    def _queue_resource(self, path):
        pending = self.__dict__.get("_pending_resources")
        if pending is None:
            return False
        pending.append(path)
        return True

    def _take_pending_resources(self):
        pending = self.__dict__.get("_pending_resources") or []
        self._pending_resources = None
        return pending

    def _set_xaml_names(self, names):
        self._xaml_names = frozenset(names)

    def _attach_root_events(self, native):
        """Bind the controller's own lifecycle handlers to a loaded root."""

    def _release(self):
        self._events.release()


class Window(_Root):
    """Own a native ``System.Windows.Window`` loaded from XAML."""

    _binding_exclude = True
    _root_slot = "_window"
    _root_type = Windows.Window

    def _initialize(self):
        if self.__dict__.get("_window") is None:
            _require_sta()
            self._window = Windows.Window()
            self._events = _EventRegistry(self._on_callback_failure)
            self._closed = False
            self._modeless = False
            self._prompt = False
        self._pending_resources = []

    def _adopt_root(self, native):
        previous = self._window
        self._window = native
        previous.Close()
        self._closed = False

    def _attach_root_events(self, native):
        self._events.bind(native, "Closed", self._on_closed, guarded=False)

    def Show(self):
        """Show the native window without creating a nested modal dispatcher."""
        self._events.raise_error()
        self._modeless = True
        self._window.Show()
        self._events.raise_error()

    def ShowDialog(self):
        """Run the modal dialog and release Python event roots even on failure."""
        try:
            self._events.raise_error()
            result = self._window.ShowDialog()
            self._events.raise_error()
            return result
        finally:
            self._release()

    def Close(self):
        """Close the native root and release callbacks, even before it is shown.

        A ``Closing`` handler that cancels the close leaves the window open
        with every callback still attached, so it keeps working.

        Raises:
            Exception: A callback of a modeless prompt failed while it was
                shown; the command that owns the prompt receives the error here.
        """
        if not self._closed:
            self._window.Close()
        if not self._closed and self._window.IsLoaded:
            return
        self._release()
        if self._modeless:
            self._events.raise_error()

    def _show_prompt(self):
        self._modeless = True
        self._prompt = True
        self._window.Show()

    def _dispose(self):
        if "_window" in self.__dict__:
            self.Close()

    def _on_callback_failure(self):
        window = self._window
        window.Dispatcher.BeginInvoke(
            System.Action(lambda: self._close_after_failure(window))
        )

    def _close_after_failure(self, window):
        if not self._closed and self._window is window:
            window.Close()

    def _on_closed(self, sender, args):
        if not System.Object.ReferenceEquals(sender, self._window):
            return
        self._closed = True
        self._release()
        if self._modeless and not self._prompt:
            self._events.report_error()


class Panel(_Root):
    """Own a native ``System.Windows.Controls.Page`` hosted by a Revit pane."""

    _binding_exclude = True
    _root_slot = "_panel"
    _root_type = framework.Controls.Page

    def _initialize(self):
        if self.__dict__.get("_panel") is None:
            _require_sta()
            self._panel = framework.Controls.Page()
            self._events = _EventRegistry(self._on_callback_failure)
        self._pending_resources = []

    def _adopt_root(self, native):
        self._panel = native

    def _dispose(self):
        if "_panel" in self.__dict__:
            self._release()

    def _on_callback_failure(self):
        self._events.report_error()


def initialize(target):
    """Prepare the controller's native root for the next ``load_component``.

    The native root is created once, on the calling STA UI thread; later calls
    keep it and its callbacks. Every call starts an empty queue of resource
    dictionaries that ``load_component`` merges into the markup.
    """
    target._initialize()


def unwrap(target):
    """Return a native root for WPF APIs that cannot consume Python controllers."""
    if isinstance(target, _Root):
        return target._root()
    return target


def dispose(target):
    """Release callbacks and host subscriptions after failed initialization."""
    if isinstance(target, _Root):
        target._dispose()


def disposing(target):
    """Return a context manager that disposes ``target`` if its body raises."""
    return Disposing(target, dispose)


def on_release(target, detach):
    """Run ``detach()`` when the form releases its callbacks.

    That happens when a window closes or finishes ``ShowDialog``, and when a
    form is disposed after a failed construction.
    """
    target._events.on_release(detach)


def queue_resource(target, path):
    """Queue a dictionary to merge into markup that has not loaded yet.

    Returns:
        bool: False once the XAML has loaded; the caller then merges the
            dictionary into the live resources itself.
    """
    return isinstance(target, _Root) and target._queue_resource(path)


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
    target._show_prompt()


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
    target._events.bind(unwrap(target), event_name, handler)


def bind_control_event(target, control, event_name, handler):
    """Keep dynamically created control callbacks within the window lifetime."""
    target._events.bind(control, event_name, handler)


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
    if not isinstance(native, target._root_type):
        raise PyRevitException(
            "CPython forms require a {} XAML root for {}.".format(
                target._root_type.__name__, type(target).__name__
            )
        )


def _swap_root(target, native, previous):
    """Make ``native`` the controller's root, carrying over the host state."""
    _require_root_type(target, native)
    _adopt_host_state(native, previous)
    target._adopt_root(native)


def _attach_xaml(target, native, prepared):
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
    target._set_xaml_names(prepared.names)
    registry = target._events
    replays = []
    for event in prepared.events:
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
    target._attach_root_events(native)
    return replays


def load_component(target, source):
    """Load a native root, resolve names, then attach retained Python handlers.

    Resource dictionaries are present during parsing so StaticResource lookup
    has the same ordering as the IronPython loader. Dictionaries queued with
    ``queue_resource`` are merged into the markup instead of the temporary
    owner, so each one, such as Theme.xaml, is parsed only once. Failures
    detach any event handlers already installed and do not subscribe to
    host-wide events.

    Note:
        Handlers attach after parsing, so events the parser raised are lost,
        except ``Checked`` and ``SelectionChanged`` where IronPython would
        have delivered them (see ``_xaml.NamedEvent``).
    """
    markup, base_uri = _read_source(source)
    if not isinstance(target, _Root):
        return _load_markup(markup, base_uri)
    previous = target._root()
    host_keys = [str(key) for key in previous.Resources.Keys if isinstance(key, str)]
    prepared = prepare_xaml(
        markup,
        _resource_sources(previous, target._take_pending_resources()),
        is_event=is_event_attribute,
        dynamic_keys=set(host_keys),
    )
    native = _load_markup(prepared.markup, base_uri)
    _swap_root(target, native, previous)
    try:
        replays = _attach_xaml(target, native, prepared)
    except Exception:
        target._release()
        raise
    for control, event_name, callback in replays:
        replay_initial_state(control, event_name, callback)
    return native
