"""Retain CPython callbacks on native WPF objects for the lifetime of a form.

Every callback a form attaches is recorded on the form so ``release_events``
detaches all of them together. A callback that raises never escapes into the
WPF dispatcher: the error is stored on the form, the form's
``_on_callback_failure`` hook runs, and ``raise_callback_error`` reports it to
the command that owns the form. Forms no command owns, such as dockable
pages and persistent modeless windows, log it through ``report_callback_error``
instead.
"""

import traceback

import clr
from pyrevit import PyRevitException, framework
from pyrevit.coreutils.logger import get_logger
from pyrevit.framework import Input, System, Windows, Media


mlogger = get_logger(__name__)
_event_attributes = {}

_MOUSE_BUTTON_EVENTS = {
    "MouseLeftButtonDown": ("MouseDown", "Left", None),
    "MouseLeftButtonUp": ("MouseUp", "Left", None),
    "MouseRightButtonDown": ("MouseDown", "Right", None),
    "MouseRightButtonUp": ("MouseUp", "Right", None),
    "PreviewMouseLeftButtonDown": ("PreviewMouseDown", "Left", None),
    "PreviewMouseLeftButtonUp": ("PreviewMouseUp", "Left", None),
    "PreviewMouseRightButtonDown": ("PreviewMouseDown", "Right", None),
    "PreviewMouseRightButtonUp": ("PreviewMouseUp", "Right", None),
    "MouseDoubleClick": ("MouseDown", "Left", 2),
    "PreviewMouseDoubleClick": ("PreviewMouseDown", "Left", 2),
}


def initialize_events(target):
    """Give a form the empty callback registries the other helpers rely on."""
    target._event_bindings = []
    target._routed_bindings = []
    target._callback_error = None


def release_events(target):
    """Detach every callback recorded on the form."""
    for control, event, handler in target._routed_bindings:
        control.RemoveHandler(event, handler)
    target._routed_bindings = []
    for control, event_name, handler in reversed(target._event_bindings):
        event = getattr(control, event_name)
        event -= handler
    target._event_bindings = []


def raise_callback_error(target):
    """Raise, once, the first error a callback stored on the form."""
    error = target._callback_error
    if error is not None:
        target._callback_error = None
        raise error


def report_callback_error(target):
    """Log, once, the first callback error of a form that no command owns."""
    error = target._callback_error
    if error is None:
        return
    target._callback_error = None
    mlogger.error(
        "pyRevit form callback failed:\n%s",
        "".join(traceback.format_exception(type(error), error, error.__traceback__)),
    )


def bind(target, control, event_name, handler):
    """Attach a guarded callback to a CLR event and record it on the form."""
    callback = _guarded(target, handler)
    event = getattr(control, event_name)
    event += callback
    target._event_bindings.append((control, event_name, callback))


def is_event_attribute(tag, attribute):
    """Return whether a XAML attribute on ``tag`` names a CLR event of that type."""
    key = (tag, attribute)
    if key not in _event_attributes:
        owner = _control_type(tag)
        _event_attributes[key] = (
            owner is not None and clr.GetClrType(owner).GetEvent(attribute) is not None
        )
    return _event_attributes[key]


def bind_template_event(target, root, tag, uid, event_name, handler):
    """Route an event declared inside a template to ``handler``.

    Template instances do not exist when the XAML loads, so their elements are
    matched by ``Uid`` (and by type, for WPF controls). Bubbling events with a
    preview counterpart get a direct handler on each matching element the
    first time the tunnelling preview event reaches it, which preserves WPF's
    handler order and ``Handled`` semantics. Other routed events are matched
    from a handler on ``root``. Direct mouse-button events are rebuilt from
    ``MouseDown``/``MouseUp`` filtered by button and click count. ``tag`` is
    the element's WPF type name, or ``{namespace}Name`` for a type outside the
    WPF namespace, which is then matched by ``Uid`` alone.

    Raises:
        PyRevitException: The event is unknown, or is a direct routed event
            such as ``Loaded`` or ``MouseEnter`` that never reaches an
            ancestor, so it cannot be observed for template instances.
    """
    owner = _control_type(tag)
    mapped = _MOUSE_BUTTON_EVENTS.get(event_name)
    routed_name, button, clicks = mapped if mapped else (event_name, None, None)
    event = _routed_event(owner, routed_name)
    if event is None:
        raise PyRevitException(
            "Unsupported template event: {}.{}".format(tag, event_name)
        )
    if event.RoutingStrategy == Windows.RoutingStrategy.Direct:
        raise PyRevitException(
            "{}.{} is a direct routed event; CPython forms cannot observe it "
            "inside templates.".format(tag, event_name)
        )
    callback = _guarded(target, handler)
    if mapped:
        callback = _mouse_button_filter(callback, button, clicks)

    def sources(args):
        return [
            element
            for element in _routing_ancestors(args.OriginalSource)
            if getattr(element, "Uid", None) == uid
            and (owner is None or isinstance(element, owner))
        ]

    preview = _routed_event(owner, "Preview" + routed_name)
    if event.RoutingStrategy == Windows.RoutingStrategy.Bubble and preview:
        _attach_on_preview(target, root, event, preview, sources, callback)
        return
    _attach_at_root(target, root, event, sources, callback)


def _guarded(target, handler):
    def invoke(sender, args):
        try:
            handler(sender, args)
        except BaseException as error:
            if target._callback_error is None:
                target._callback_error = error
            target._on_callback_failure()

    return invoke


def _mouse_button_filter(callback, button, clicks):
    expected = getattr(Input.MouseButton, button)

    def filtered(sender, args):
        if args.ChangedButton != expected:
            return
        if clicks is not None and args.ClickCount != clicks:
            return
        callback(sender, args)

    return filtered


def _control_type(tag):
    if tag.startswith("{"):
        return None
    namespaces = (
        framework.Controls,
        framework.Controls.Primitives,
        framework.Documents,
        framework.Windows,
    )
    return next(
        (
            getattr(namespace, tag)
            for namespace in namespaces
            if hasattr(namespace, tag)
        ),
        None,
    )


def _routed_event(owner, event_name):
    if owner is not None:
        return getattr(owner, event_name + "Event", None)
    matches = [
        event
        for event in Windows.EventManager.GetRoutedEvents()
        if event.Name == event_name
    ]
    return matches[0] if len(matches) == 1 else None


def _routing_ancestors(source):
    current = source
    while current is not None:
        yield current
        if isinstance(current, (Media.Visual, Media.Media3D.Visual3D)):
            current = Media.VisualTreeHelper.GetParent(current)
        else:
            current = Windows.LogicalTreeHelper.GetParent(current)


def _attach_on_preview(target, root, event, preview, sources, callback):
    direct = Windows.RoutedEventHandler(callback)
    attached = []

    def discover(sender, args):
        for element in sources(args):
            if not any(System.Object.ReferenceEquals(element, e) for e in attached):
                element.AddHandler(event, direct)
                attached.append(element)
                target._routed_bindings.append((element, event, direct))

    delegate = Windows.RoutedEventHandler(discover)
    root.AddHandler(preview, delegate, True)
    target._routed_bindings.append((root, preview, delegate))


def _attach_at_root(target, root, event, sources, callback):
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
    root.AddHandler(event, delegate)
    target._routed_bindings.append((root, event, delegate))
