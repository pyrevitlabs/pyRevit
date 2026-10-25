"""Own native modal WPF windows through composition rather than CLR subclasses.

Important:
    Python controllers never become CLR-derived types. This avoids pythonnet
    type-registration collisions on repeated commands and reloads. Arbitrary
    custom XAML, data-bound Python models and modeless windows are not promised.
"""

import io
import os.path as op

from pyrevit import PyRevitCPythonNotSupported, PyRevitException
from pyrevit import framework
from pyrevit.framework import System, Windows, Uri, UriKind
from System.Windows.Markup import XamlReader, ParserContext

from .._xaml import prepare_xaml


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
            setattr(window, name, value)
        else:
            object.__setattr__(self, name, value)

    def Show(self):
        """Reject modeless use until callback lifetime and API scheduling are supported."""
        self.Close()
        raise PyRevitCPythonNotSupported("pyrevit.forms.WPFWindow.Show")

    def ShowDialog(self):
        """Run the modal dialog and release Python event roots even on failure."""
        try:
            if self._callback_error is not None:
                raise self._callback_error
            result = self._window.ShowDialog()
            if self._callback_error is not None:
                raise self._callback_error
            return result
        finally:
            self._unsubscribe_theme_changed()
            _release_events(self)

    def Close(self):
        """Close the native root and release callbacks even before it is shown."""
        try:
            self._window.Close()
        finally:
            self._unsubscribe_theme_changed()
            _release_events(self)

    def _on_closed(self, sender, args):
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
    target._callback_error = None


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
    """Expose string items through a managed collection understood by WPF."""
    return framework.to_clr_list(System.String, [str(value) for value in values])


def validate_input(value_type):
    """Reject modes that depend on Python model binding until that tier lands."""
    if value_type not in ("string", "date", "slider"):
        raise PyRevitCPythonNotSupported(
            "pyrevit.forms.GetValueWindow.{}".format(value_type)
        )


def _release_events(target):
    for control, event_name, handler in reversed(target._event_bindings):
        event = getattr(control, event_name)
        event -= handler
    target._event_bindings = []


def _event_handler(target, handler):
    def invoke(sender, args):
        try:
            handler(sender, args)
        except Exception as error:
            target._callback_error = error
            target.Close()

    return invoke


def _bind(target, control, event_name, handler):
    callback = _event_handler(target, handler)
    event = getattr(control, event_name)
    event += callback
    target._event_bindings.append((control, event_name, callback))


def bind_event(target, event_name, handler):
    """Retain native event callbacks until close, then detach them together."""
    _bind(target, unwrap(target), event_name, handler)


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
    markup, names, events = prepare_xaml(markup, sources)
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
    previous.Close()
    try:
        for name in names:
            control = native.FindName(name)
            if control is None:
                raise PyRevitException(
                    "CPython XAML name was not found: {}".format(name)
                )
            object.__setattr__(target, name, control)
        for name, event_name, handler_name in events:
            control = getattr(target, name)
            _bind(target, control, event_name, getattr(target, handler_name))
        native.Closed += target._on_closed
        target._event_bindings.append((native, "Closed", target._on_closed))
    except Exception:
        _release_events(target)
        raise
    return native
