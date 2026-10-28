"""Retain CPython callbacks on native WPF objects for the lifetime of a form.

Every callback a form attaches is recorded in the form's ``_EventRegistry`` so
``release`` detaches all of them together. A callback that raises never
escapes into the WPF dispatcher: the registry stores the error and runs the
form's failure hook, and the command that owns the form receives the error
from ``raise_error``. Forms no command owns, such as dockable pages and
persistent modeless windows, log it through ``report_error`` instead.
"""

import re
import traceback

import clr
from pyrevit import PyRevitException, framework
from pyrevit.coreutils.logger import get_logger
from pyrevit.framework import Input, System, Windows, Media


mlogger = get_logger(__name__)
_event_attributes = {}
_CLR_NAMESPACE_TAG = re.compile(
    r"^\{clr-namespace:([^;}]*)(?:;assembly=([^}]+))?\}(.+)$"
)

_MOUSE_BUTTON_EVENTS = {
    "MouseLeftButtonDown": ("MouseDown", ("Left",), None),
    "MouseLeftButtonUp": ("MouseUp", ("Left",), None),
    "MouseRightButtonDown": ("MouseDown", ("Right",), None),
    "MouseRightButtonUp": ("MouseUp", ("Right",), None),
    "PreviewMouseLeftButtonDown": ("PreviewMouseDown", ("Left",), None),
    "PreviewMouseLeftButtonUp": ("PreviewMouseUp", ("Left",), None),
    "PreviewMouseRightButtonDown": ("PreviewMouseDown", ("Right",), None),
    "PreviewMouseRightButtonUp": ("PreviewMouseUp", ("Right",), None),
    "MouseDoubleClick": ("MouseDown", ("Left", "Right"), 2),
    "PreviewMouseDoubleClick": ("PreviewMouseDown", ("Left", "Right"), 2),
}


class _EventRegistry(object):
    """Own every callback one form attached to native WPF objects.

    Invariant:
        ``release`` detaches everything recorded so far and may run any
        number of times; a released registry keeps accepting new callbacks.
        Only the first callback error is kept until it is raised or reported.
    """

    def __init__(self, on_failure):
        self._events = []
        self._routed = []
        self._detachers = []
        self._error = None
        self._on_failure = on_failure

    @property
    def is_released(self):
        """Whether no callback or release hook is currently attached."""
        return not (self._events or self._routed or self._detachers)

    @property
    def error(self):
        """The stored callback error, or None."""
        return self._error

    def bind(self, control, event_name, handler, guarded=True):
        """Attach a callback to a CLR event and record it.

        A guarded callback routes exceptions to the registry instead of the
        WPF dispatcher; lifecycle handlers that must not close the form on
        failure pass ``guarded=False``.

        Returns:
            callable: The attached callback, for ``replay_initial_state``.
        """
        callback = self.guard(handler) if guarded else handler
        event = getattr(control, event_name)
        event += callback
        self._events.append((control, event_name, callback))
        return callback

    def add_routed(self, element, routed_event, delegate, handled_too=False):
        """Add a routed-event handler that ``release`` removes."""
        if handled_too:
            element.AddHandler(routed_event, delegate, True)
        else:
            element.AddHandler(routed_event, delegate)
        self._routed.append((element, routed_event, delegate))

    def on_release(self, detach):
        """Run ``detach()`` once, on the next ``release``."""
        self._detachers.append(detach)

    def release(self):
        """Detach every recorded callback and run the release hooks."""
        detachers, self._detachers = self._detachers, []
        for detach in detachers:
            detach()
        routed, self._routed = self._routed, []
        for element, routed_event, delegate in routed:
            element.RemoveHandler(routed_event, delegate)
        events, self._events = self._events, []
        for control, event_name, handler in reversed(events):
            event = getattr(control, event_name)
            event -= handler

    def guard(self, handler):
        """Wrap ``handler`` so an exception is stored rather than raised."""

        def invoke(sender, args):
            try:
                handler(sender, args)
            except BaseException as error:
                if self._error is None:
                    self._error = error
                self._on_failure()

        return invoke

    def raise_error(self):
        """Raise, once, the first stored callback error."""
        error = self._error
        if error is not None:
            self._error = None
            raise error

    def report_error(self):
        """Log, once, the first stored error of a form that no command owns."""
        error = self._error
        if error is None:
            return
        self._error = None
        mlogger.error(
            "pyRevit form callback failed:\n%s",
            "".join(
                traceback.format_exception(type(error), error, error.__traceback__)
            ),
        )


def replay_initial_state(control, event_name, callback):
    """Run ``callback`` once for state the XAML parser set before it attached.

    Handlers are attached after ``XamlReader.Load``, so ``Checked`` for a
    toggle that loads checked and ``SelectionChanged`` for a selector that
    loads with a selection were raised before any handler existed. The loader
    calls this only for events whose ``NamedEvent.replay`` is set, which is
    where IronPython's attribute-ordered loader would have delivered them;
    the loaded state then decides whether anything is raised. ``TextChanged``,
    ``ValueChanged`` and other events raised during parsing are not replayed.
    """
    primitives = framework.Controls.Primitives
    if event_name == "Checked":
        if isinstance(control, primitives.ToggleButton) and control.IsChecked is True:
            args = Windows.RoutedEventArgs(
                primitives.ToggleButton.CheckedEvent, control
            )
            callback(control, args)
    elif event_name == "SelectionChanged":
        if isinstance(control, primitives.Selector) and control.SelectedIndex >= 0:
            selected = getattr(control, "SelectedItems", None)
            added = System.Collections.ArrayList()
            for item in selected if selected is not None else [control.SelectedItem]:
                added.Add(item)
            args = framework.Controls.SelectionChangedEventArgs(
                primitives.Selector.SelectionChangedEvent,
                System.Collections.ArrayList(),
                added,
            )
            args.Source = control
            callback(control, args)


def is_event_attribute(tag, attribute):
    """Return whether a XAML attribute on ``tag`` names a CLR event of that type.

    ``tag`` is a WPF type name or ``{clr-namespace:Ns;assembly=Asm}Name``;
    custom types resolve through the loaded assemblies. Unresolvable types
    report False, leaving ``_xaml._EVENTS`` as the fallback.
    """
    key = (tag, attribute)
    if key not in _event_attributes:
        owner = _clr_type(tag)
        _event_attributes[key] = (
            owner is not None and owner.GetEvent(attribute) is not None
        )
    return _event_attributes[key]


def bind_template_event(registry, root, tag, uid, event_name, handler):
    """Route an event declared inside a template to ``handler``.

    Template instances do not exist when the XAML loads, so their elements are
    matched by ``Uid`` (and by type, for WPF controls). Bubbling events with a
    preview counterpart get a direct handler on each matching element the
    first time the tunnelling preview event reaches it, which preserves WPF's
    handler order and ``Handled`` semantics. Other routed events are matched
    from a handler on ``root``. Direct mouse-button events are rebuilt from
    ``MouseDown``/``MouseUp`` filtered by button and click count; double
    clicks accept the left or right button with ``ClickCount == 2``, as
    ``Control.MouseDoubleClick`` does. An element that unloads drops its
    direct handler and is rediscovered if it loads again. ``tag`` is
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
    callback = registry.guard(handler)
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
        _attach_on_preview(registry, root, event, preview, sources, callback)
        return
    _attach_at_root(registry, root, event, sources, callback)


def _mouse_button_filter(callback, buttons, clicks):
    expected = [getattr(Input.MouseButton, button) for button in buttons]

    def filtered(sender, args):
        if args.ChangedButton not in expected:
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


def _clr_namespace_type(tag):
    match = _CLR_NAMESPACE_TAG.match(tag)
    if match is None:
        return None
    namespace, assembly, name = match.groups()
    full_name = "{}.{}".format(namespace, name) if namespace else name
    try:
        if assembly:
            resolved = System.Type.GetType("{}, {}".format(full_name, assembly))
            if resolved is not None:
                return resolved
        for loaded in System.AppDomain.CurrentDomain.GetAssemblies():
            resolved = loaded.GetType(full_name)
            if resolved is not None:
                return resolved
    except Exception:
        return None
    return None


def _clr_type(tag):
    if tag.startswith("{"):
        return _clr_namespace_type(tag)
    owner = _control_type(tag)
    return None if owner is None else clr.GetClrType(owner)


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


def _identity(element):
    return System.Runtime.CompilerServices.RuntimeHelpers.GetHashCode(element)


def _attach_on_preview(registry, root, event, preview, sources, callback):
    direct = Windows.RoutedEventHandler(callback)
    attached = {}

    def find(element):
        for known in attached.get(_identity(element), ()):
            if System.Object.ReferenceEquals(element, known):
                return known
        return None

    def detach(element):
        element.RemoveHandler(event, direct)
        if isinstance(
            element, (Windows.FrameworkElement, Windows.FrameworkContentElement)
        ):
            element.Unloaded -= unloaded

    def forget(sender, args):
        element = find(sender)
        if element is None:
            return
        detach(element)
        key = _identity(element)
        bucket = [
            known
            for known in attached[key]
            if not System.Object.ReferenceEquals(element, known)
        ]
        if bucket:
            attached[key] = bucket
        else:
            del attached[key]

    unloaded = Windows.RoutedEventHandler(forget)

    def discover(sender, args):
        for element in sources(args):
            if find(element) is None:
                element.AddHandler(event, direct)
                if isinstance(
                    element, (Windows.FrameworkElement, Windows.FrameworkContentElement)
                ):
                    element.Unloaded += unloaded
                attached.setdefault(_identity(element), []).append(element)

    def release():
        for bucket in list(attached.values()):
            for element in bucket:
                detach(element)
        attached.clear()

    registry.add_routed(root, preview, Windows.RoutedEventHandler(discover), True)
    registry.on_release(release)


def _attach_at_root(registry, root, event, sources, callback):
    tunnels = event.RoutingStrategy == Windows.RoutingStrategy.Tunnel

    def routed(sender, args):
        matches = sources(args)
        if tunnels:
            matches.reverse()
        for element in matches:
            callback(element, args)
            if args.Handled:
                break

    registry.add_routed(root, event, Windows.RoutedEventHandler(routed))
