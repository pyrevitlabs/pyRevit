"""Own native modal WPF windows through composition rather than CLR subclasses.

Important:
    Python controllers never become CLR-derived types. This avoids pythonnet
    type-registration collisions on repeated commands and reloads. Reactive
    models use managed binding adapters; persistent modeless windows remain
    unsupported.
"""

import io
import os.path as op

from pyrevit import PyRevitCPythonNotSupported, PyRevitException
from pyrevit import framework
from pyrevit.coreutils import envvars
from pyrevit.framework import Interop, System, Windows, Media, Uri, UriKind
from System.Windows.Markup import XamlReader, ParserContext

from .._xaml import prepare_xaml
from ._binding import Reactive, binding_source, unwrap_item


class Window(object):
    """Forward window properties to a native WPF root owned by this controller."""

    def __getattr__(self, name):
        window = self.__dict__.get("_window")
        if window is None:
            raise AttributeError(name)
        return getattr(window, name)

    def __setattr__(self, name, value):
        window = self.__dict__.get("_window")
        if not name.startswith("_") and window is not None and hasattr(window, name):
            if name == "DataContext":
                value = binding_source(value)
            setattr(window, name, value)
        else:
            object.__setattr__(self, name, value)

    def Show(self):
        """Show the native window without creating a nested modal dispatcher."""
        _raise_callback_error(self)
        self._modeless = True
        self._window.Show()
        _raise_callback_error(self)

    def ShowDialog(self):
        """Run the modal dialog and release Python event roots even on failure."""
        try:
            _raise_callback_error(self)
            result = self._window.ShowDialog()
            _raise_callback_error(self)
            return result
        finally:
            self._unsubscribe_theme_changed()
            _release_events(self)

    def Close(self):
        """Close the native root and release callbacks even before it is shown.

        Raises:
            Exception: A callback of a modeless prompt failed while it was
                shown; the command that owns the prompt receives the error here.
        """
        try:
            if not self._closed:
                self._window.Close()
        finally:
            self._unsubscribe_theme_changed()
            _release_events(self)
        if self._modeless:
            _raise_callback_error(self)

    def _on_closed(self, sender, args):
        self._closed = True
        self._unsubscribe_theme_changed()
        _release_events(self)


def initialize(target):
    """Create the temporary resource owner on the calling STA UI thread."""
    if (
        System.Threading.Thread.CurrentThread.GetApartmentState()
        != System.Threading.ApartmentState.STA
    ):
        raise PyRevitException(
            "CPython forms must be created on Revit's STA UI thread."
        )
    target._window = Windows.Window()
    target._event_bindings = []
    target._routed_bindings = []
    target._callback_error = None
    target._closed = False
    target._modeless = False


def unwrap(target):
    """Return a native root for WPF APIs that cannot consume Python controllers."""
    if isinstance(target, Window):
        return target._window
    return target


def dispose(target):
    """Release callbacks and host subscriptions after failed initialization."""
    if "_window" in target.__dict__:
        target.Close()


def items_source(values):
    """Expose Python values through a managed collection understood by WPF."""
    return framework.to_clr_list(System.Object, values)


def list_source(values):
    """Bind list models without losing original Python object identity."""
    return items_source([binding_source(value) for value in values])


def show_prompt(target):
    """Show an overlay whose enclosing command owns its complete lifetime."""
    target._modeless = True
    target._window.Show()


def validate_input(value_type):
    """Reject unknown input modes before creating native controls."""
    if value_type not in ("string", "date", "slider", "dropdown"):
        raise PyRevitCPythonNotSupported(
            "pyrevit.forms.GetValueWindow.{}".format(value_type)
        )


def activate_open_window(envvar):
    """Activate a still-open CPython modeless window stored in an environment variable."""
    window = envvars.get_pyrevit_env_var(envvar)
    if not isinstance(window, Window) or window._closed:
        envvars.set_pyrevit_env_var(envvar, None)
        return False
    native = unwrap(window)
    if Interop.WindowInteropHelper(native).Handle == System.IntPtr.Zero:
        envvars.set_pyrevit_env_var(envvar, None)
        return False
    if native.IsVisible:
        if native.WindowState == Windows.WindowState.Minimized:
            native.WindowState = Windows.WindowState.Normal
        native.Activate()
    return True


def _release_events(target):
    for control, event, handler in target._routed_bindings:
        control.RemoveHandler(event, handler)
    target._routed_bindings = []
    for control, event_name, handler in reversed(target._event_bindings):
        event = getattr(control, event_name)
        event -= handler
    target._event_bindings = []


def _raise_callback_error(target):
    error = target._callback_error
    if error is not None:
        target._callback_error = None
        raise error


def _close_after_failure(target, window):
    if not target._closed and target._window is window:
        window.Close()


def _event_handler(target, handler):
    def invoke(sender, args):
        try:
            handler(sender, args)
        except Exception as error:
            if target._callback_error is None:
                target._callback_error = error
            window = target._window
            window.Dispatcher.BeginInvoke(
                System.Action(lambda: _close_after_failure(target, window))
            )

    return invoke


def _bind(target, control, event_name, handler):
    callback = _event_handler(target, handler)
    event = getattr(control, event_name)
    event += callback
    target._event_bindings.append((control, event_name, callback))


def bind_event(target, event_name, handler):
    """Retain native event callbacks until close, then detach them together."""
    _bind(target, unwrap(target), event_name, handler)


def bind_control_event(target, control, event_name, handler):
    """Keep dynamically created control callbacks within the window lifetime."""
    _bind(target, control, event_name, handler)


def _routing_ancestors(source):
    current = source
    while current is not None:
        yield current
        if isinstance(current, (Media.Visual, Media.Media3D.Visual3D)):
            current = Media.VisualTreeHelper.GetParent(current)
        else:
            current = Windows.LogicalTreeHelper.GetParent(current)


def _bind_template_event(target, tag, uid, event_name, handler):
    owner = next(
        (
            getattr(namespace, tag)
            for namespace in (
                framework.Controls,
                framework.Controls.Primitives,
                framework.Documents,
            )
            if hasattr(namespace, tag)
        ),
        None,
    )
    event = getattr(owner, event_name + "Event", None) if owner else None
    if event is None:
        raise PyRevitException(
            "Unsupported template event: {}.{}".format(tag, event_name)
        )
    callback = _event_handler(target, handler)

    def sources(args):
        return [
            element
            for element in _routing_ancestors(args.OriginalSource)
            if isinstance(element, owner) and element.Uid == uid
        ]

    preview = getattr(owner, "Preview" + event_name + "Event", None)
    if event.RoutingStrategy == Windows.RoutingStrategy.Bubble and preview:
        direct = Windows.RoutedEventHandler(callback)
        attached = []

        def discover(sender, args):
            for element in sources(args):
                if not any(System.Object.ReferenceEquals(element, e) for e in attached):
                    element.AddHandler(event, direct)
                    attached.append(element)
                    target._routed_bindings.append((element, event, direct))

        delegate = Windows.RoutedEventHandler(discover)
        target._window.AddHandler(preview, delegate, True)
        target._routed_bindings.append((target._window, preview, delegate))
        return

    tunnels = event.RoutingStrategy == Windows.RoutingStrategy.Tunnel

    def routed(sender, args):
        matches = sources(args)
        if tunnels:
            matches.reverse()
        for element in matches:
            callback(element, args)
            if args.Handled:
                break

    delegate = Windows.RoutedEventHandler(routed)
    target._window.AddHandler(event, delegate)
    target._routed_bindings.append((target._window, event, delegate))


def _find_resource_name(native, name, owner_name, key):
    owner = native if owner_name is None else native.FindName(owner_name)
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
        with io.open(source, encoding="utf-8-sig") as stream:
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
    has the same ordering as the IronPython loader. Failures detach any event
    handlers already installed and do not subscribe to host-wide events.
    """
    markup, base_uri = _read_source(source)
    if not isinstance(target, Window):
        return _load_markup(markup, base_uri)
    previous = target._window
    resources = previous.Resources
    sources = [str(item.Source) for item in resources.MergedDictionaries]
    markup, names, events, resource_names = prepare_xaml(markup, sources)
    native = _load_markup(markup, base_uri)
    if not isinstance(native, Windows.Window):
        raise PyRevitException("CPython WPFWindow requires a Window XAML root.")
    for key in resources.Keys:
        if not native.Resources.Contains(key):
            native.Resources[key] = resources[key]
    for name in ("Background", "Foreground"):
        prop = getattr(framework.Controls.Control, name + "Property")
        if native.ReadLocalValue(prop) == Windows.DependencyProperty.UnsetValue:
            setattr(native, name, getattr(previous, name))
    target._window = native
    target._closed = False
    previous.Close()
    try:
        for name in names:
            if name in resource_names:
                control = _find_resource_name(native, name, *resource_names[name])
            else:
                control = native.FindName(name)
            if control is None:
                raise PyRevitException(
                    "CPython XAML name was not found: {}".format(name)
                )
            object.__setattr__(target, name, control)
        for name, event_name, handler_name in events:
            if name.startswith("@template:"):
                _, tag, uid = name.split(":", 2)
                _bind_template_event(
                    target,
                    tag,
                    uid,
                    event_name,
                    getattr(target, handler_name),
                )
            else:
                control = getattr(target, name)
                _bind(target, control, event_name, getattr(target, handler_name))
        native.Closed += target._on_closed
        target._event_bindings.append((native, "Closed", target._on_closed))
    except Exception:
        _release_events(target)
        raise
    return native
