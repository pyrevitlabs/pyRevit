"""Own native modal WPF windows through composition rather than CLR subclasses.

Important:
    Python controllers never become CLR-derived types. This avoids pythonnet
    type-registration collisions on repeated commands and reloads. Reactive
    models use managed binding adapters, and modal, modeless and dockable roots
    share the same callback lifetime rules.
"""

import os.path as op

from pyrevit import PyRevitCPythonNotSupported, PyRevitException
from pyrevit import framework
from pyrevit.coreutils import envvars
from pyrevit.framework import Interop, System, Windows, Uri, UriKind
from System.Windows.Markup import XamlReader, ParserContext

from .._xaml import prepare_xaml
from ._binding import Reactive, binding_source, unwrap_item
from ._events import (
    bind,
    bind_template_event,
    initialize_events,
    is_event_attribute,
    raise_callback_error,
    release_events,
    replay_initial_state,
    report_callback_error,
)


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


class Window(object):
    """Forward window properties to a native WPF root owned by this controller.

    Assigning ``DataContext`` keeps the Python model alive as long as the
    controller, and reading it returns that Python model rather than its
    native binding adapter.
    """

    def __getattr__(self, name):
        return _forward_get(self.__dict__.get("_window"), name)

    def __setattr__(self, name, value):
        _forward_set(self, self.__dict__.get("_window"), name, value)

    def Show(self):
        """Show the native window without creating a nested modal dispatcher."""
        raise_callback_error(self)
        self._modeless = True
        self._window.Show()
        raise_callback_error(self)

    def ShowDialog(self):
        """Run the modal dialog and release Python event roots even on failure."""
        try:
            raise_callback_error(self)
            result = self._window.ShowDialog()
            raise_callback_error(self)
            return result
        finally:
            self._unsubscribe_theme_changed()
            release_events(self)

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
        self._unsubscribe_theme_changed()
        release_events(self)
        if self._modeless:
            raise_callback_error(self)

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
        self._unsubscribe_theme_changed()
        release_events(self)
        if self._modeless and not self._prompt:
            report_callback_error(self)


class Panel(object):
    """Forward panel properties to a native WPF page owned by this controller.

    ``DataContext`` follows the same lifetime and unwrapping rules as
    ``Window``.
    """

    def __getattr__(self, name):
        return _forward_get(self.__dict__.get("_panel"), name)

    def __setattr__(self, name, value):
        _forward_set(self, self.__dict__.get("_panel"), name, value)

    def _on_callback_failure(self):
        report_callback_error(self)


def _require_sta():
    if (
        System.Threading.Thread.CurrentThread.GetApartmentState()
        != System.Threading.ApartmentState.STA
    ):
        raise PyRevitException(
            "CPython forms must be created on Revit's STA UI thread."
        )


def initialize(target):
    """Prepare the temporary resource owner for the next ``load_component``.

    The native window is created once, on the calling STA UI thread; later
    calls keep it and its callbacks. Every call starts an empty list of
    resource dictionaries that ``load_component`` merges into the markup.
    """
    if target.__dict__.get("_window") is None:
        _require_sta()
        target._window = Windows.Window()
        initialize_events(target)
        target._closed = False
        target._modeless = False
        target._prompt = False
    target._pending_resources = []


def initialize_panel(target):
    """Create a native page resource owner on the calling STA UI thread."""
    _require_sta()
    target._panel = framework.Controls.Page()
    initialize_events(target)
    target._pending_resources = []


def unwrap(target):
    """Return a native root for WPF APIs that cannot consume Python controllers."""
    if isinstance(target, Window):
        return target._window
    if isinstance(target, Panel):
        return target._panel
    return target


def dispose(target):
    """Release callbacks and host subscriptions after failed initialization."""
    if isinstance(target, Window) and "_window" in target.__dict__:
        target.Close()
    if isinstance(target, Panel) and "_panel" in target.__dict__:
        target._unsubscribe_theme_changed()
        release_events(target)


def items_source(values):
    """Expose Python values through a managed collection understood by WPF."""
    return framework.to_clr_list(System.Object, values)


def list_source(values):
    """Bind list models without losing original Python object identity."""
    return items_source([binding_source(value) for value in values])


def show_prompt(target):
    """Show an overlay whose enclosing command owns its complete lifetime."""
    target._modeless = True
    target._prompt = True
    target._window.Show()


def validate_input(value_type):
    """Reject unknown input modes before creating native controls."""
    if value_type not in ("string", "date", "slider", "dropdown"):
        raise PyRevitCPythonNotSupported(
            "pyrevit.forms.GetValueWindow.{}".format(value_type)
        )


def make_pane_provider(panel, default_visible):
    """Build the Revit pane provider that hosts a CPython page's native root.

    The provider is a managed type so Revit never calls back into a Python
    implementation of ``IDockablePaneProvider``.
    """
    from pyrevit.runtime.types import DockablePaneProvider

    provider = DockablePaneProvider(unwrap(panel), default_visible)
    if panel.initial_state is not None:
        provider.InitialState = panel.initial_state
    if panel.editor_interaction is not None:
        provider.EditorInteraction = panel.editor_interaction
    if panel.contextual_help is not None:
        provider.ContextualHelp = panel.contextual_help
    return provider


def activate_open_window(envvar):
    """Activate a still-open CPython modeless window stored in an environment variable.

    Openness is judged by the native window handle, not the controller's class,
    so a window created before ``pyrevit.forms`` was re-imported still counts.
    """
    window = envvars.get_pyrevit_env_var(envvar)
    if window is None:
        return False
    native = getattr(window, "_window", window)
    try:
        is_open = Interop.WindowInteropHelper(native).Handle != System.IntPtr.Zero
    except Exception:
        is_open = False
    if not is_open:
        envvars.set_pyrevit_env_var(envvar, None)
        return False
    if native.IsVisible:
        if native.WindowState == Windows.WindowState.Minimized:
            native.WindowState = Windows.WindowState.Normal
        native.Activate()
    return True


def bind_event(target, event_name, handler):
    """Retain native event callbacks until close, then detach them together."""
    bind(target, unwrap(target), event_name, handler)


def bind_control_event(target, control, event_name, handler):
    """Keep dynamically created control callbacks within the window lifetime."""
    bind(target, control, event_name, handler)


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


def load_component(target, source):
    """Load a native root, resolve names, then attach retained Python handlers.

    Resource dictionaries are present during parsing so StaticResource lookup
    has the same ordering as the IronPython loader. Dictionaries queued in
    ``_pending_resources`` are merged into the markup instead of the temporary
    owner, so each one, such as Theme.xaml, is parsed only once. Failures
    detach any event handlers already installed and do not subscribe to
    host-wide events.

    Note:
        Handlers attach after parsing, so events the parser raised are lost,
        except ``Checked`` and ``SelectionChanged``, which are replayed once
        from the loaded state (see ``replay_initial_state``).
    """
    markup, base_uri = _read_source(source)
    if not isinstance(target, (Window, Panel)):
        return _load_markup(markup, base_uri)
    previous = unwrap(target)
    resources = previous.Resources
    sources = []
    pending = target.__dict__.get("_pending_resources") or []
    for source_uri in [str(item.Source) for item in resources.MergedDictionaries] + [
        str(Uri(path, UriKind.Absolute)) for path in pending
    ]:
        if source_uri not in sources:
            sources.append(source_uri)
    host_keys = [str(key) for key in resources.Keys if isinstance(key, str)]
    markup, names, events, resource_names = prepare_xaml(
        markup, sources, is_event=is_event_attribute, dynamic_keys=set(host_keys)
    )
    native = _load_markup(markup, base_uri)
    if isinstance(target, Window) and not isinstance(native, Windows.Window):
        raise PyRevitException("CPython WPFWindow requires a Window XAML root.")
    if isinstance(target, Panel) and not isinstance(native, framework.Controls.Page):
        raise PyRevitException("CPython WPFPanel requires a Page XAML root.")
    for key in resources.Keys:
        if not native.Resources.Contains(key):
            native.Resources[key] = resources[key]
    for name in ("Background", "Foreground"):
        prop = getattr(framework.Controls.Control, name + "Property")
        if native.ReadLocalValue(prop) == Windows.DependencyProperty.UnsetValue:
            setattr(native, name, getattr(previous, name))
    if isinstance(target, Window):
        target._window = native
        previous.Close()
        target._closed = False
    else:
        target._panel = native
    try:
        for name in names:
            control = _find_name(native, name, resource_names)
            if control is None:
                raise PyRevitException(
                    "CPython XAML name was not found: {}".format(name)
                )
            object.__setattr__(target, name, control)
        target._xaml_names = frozenset(names)
        replays = []
        for name, event_name, handler_name in events:
            if name.startswith("@template:"):
                _, uid, tag = name.split(":", 2)
                bind_template_event(
                    target,
                    native,
                    tag,
                    uid,
                    event_name,
                    getattr(target, handler_name),
                )
            else:
                control = getattr(target, name)
                callback = bind(
                    target, control, event_name, getattr(target, handler_name)
                )
                replays.append((control, event_name, callback))
        if isinstance(target, Window):
            native.Closed += target._on_closed
            target._event_bindings.append((native, "Closed", target._on_closed))
    except Exception:
        release_events(target)
        raise
    target._pending_resources = None
    for control, event_name, callback in replays:
        replay_initial_state(control, event_name, callback)
    return native
