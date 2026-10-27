"""Retain CPython callbacks on native WPF objects for the lifetime of a form.

Every callback a form attaches is recorded on the form so ``release_events``
detaches all of them together. A callback that raises never escapes into the
WPF dispatcher: the error is stored on the form, the form's
``_on_callback_failure`` hook runs, and ``raise_callback_error`` reports it to
the command that owns the form.
"""

from pyrevit import PyRevitException, framework
from pyrevit.framework import System, Windows, Media


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


def bind(target, control, event_name, handler):
    """Attach a guarded callback to a CLR event and record it on the form."""
    callback = _guarded(target, handler)
    event = getattr(control, event_name)
    event += callback
    target._event_bindings.append((control, event_name, callback))


def bind_template_event(target, root, tag, uid, event_name, handler):
    """Route an event declared inside a template to ``handler``.

    Template instances do not exist when the XAML loads, so their elements are
    matched by ``tag`` type and ``Uid``. Bubbling events with a preview
    counterpart get a direct handler on each matching element the first time
    the tunnelling preview event reaches it, which preserves WPF's handler
    order and ``Handled`` semantics. Other routed events are matched from a
    handler on ``root``.

    Raises:
        PyRevitException: ``tag`` names no known control with ``event_name``.
    """
    owner = _control_type(tag)
    event = getattr(owner, event_name + "Event", None) if owner else None
    if event is None:
        raise PyRevitException(
            "Unsupported template event: {}.{}".format(tag, event_name)
        )
    callback = _guarded(target, handler)

    def sources(args):
        return [
            element
            for element in _routing_ancestors(args.OriginalSource)
            if isinstance(element, owner) and element.Uid == uid
        ]

    preview = getattr(owner, "Preview" + event_name + "Event", None)
    if event.RoutingStrategy == Windows.RoutingStrategy.Bubble and preview:
        _attach_on_preview(target, root, event, preview, sources, callback)
        return
    _attach_at_root(target, root, event, sources, callback)


def _guarded(target, handler):
    def invoke(sender, args):
        try:
            handler(sender, args)
        except Exception as error:
            if target._callback_error is None:
                target._callback_error = error
            target._on_callback_failure()

    return invoke


def _control_type(tag):
    namespaces = (
        framework.Controls,
        framework.Controls.Primitives,
        framework.Documents,
    )
    return next(
        (
            getattr(namespace, tag)
            for namespace in namespaces
            if hasattr(namespace, tag)
        ),
        None,
    )


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
