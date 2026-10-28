"""Prepare trusted dialog XAML for pythonnet without losing namespace prefixes.

Control events are deferred until the native tree exists, so events the parser
raises while applying initial state never reach them. The CPython backend
replays ``Checked`` and ``SelectionChanged`` afterwards only where IronPython's
loader would have delivered them (see ``NamedEvent.replay``). Templates retain
their own namescopes; their event sources are tagged with ``Uid``, which
template instances keep, so routed handlers on the root window can match the
authored element. Template elements inside a ``ContextMenu`` or ``ToolTip``,
whose events never reach the window, are marked with ``PythonEvents.Hook``
instead, which hands each instance to the backend as WPF creates it.
"""

import re
import uuid
from collections import namedtuple
from xml.dom import minidom


class PreparedXaml(
    namedtuple("PreparedXaml", "markup names events resource_names root_properties")
):
    """Markup ready for ``XamlReader`` plus what must be attached after loading.

    Attributes:
        markup (str): Markup without deferred event attributes.
        names (list[str]): Element names outside templates, including
            generated ones for unnamed event sources.
        events (list[NamedEvent | TemplateEvent | HookedEvent]): Deferred
            handlers, in document order.
        resource_names (dict): {name: (owner name or None for the root,
            resource key)} for names declared inside resource entries, which
            WPF keeps out of the window namescope.
        root_properties (frozenset[str]): Members the root element sets as
            plain attributes or ``Root.Member`` property elements.
    """

    __slots__ = ()


class NamedEvent(namedtuple("NamedEvent", "name event handler replay")):
    """A handler deferred from a named element outside any template.

    Attributes:
        replay (bool): Whether the backend replays the initial ``Checked`` or
            ``SelectionChanged`` once the handler is attached.

    Invariant:
        ``replay`` mirrors IronPython's ``LoadComponent``, which attaches
        handlers in attribute order and applies child elements after every
        attribute: it is True when the element's initial state takes effect
        after the event attribute (for example ``Checked`` before
        ``IsChecked``), or when no state attribute sets it. A selection takes
        effect once both its state and its items exist; child items, ``Items``
        and ``ItemsSource`` property elements and state property elements all
        count as after every attribute, while an ``ItemsSource`` attribute
        counts at its own position. It is always False for other events.
    """

    __slots__ = ()


class HookedEvent(namedtuple("HookedEvent", "key event handler")):
    """A handler deferred from a template element inside a popup tree.

    Attributes:
        key (str): ``PythonEvents.Hook`` value of the element, unique to this
            preparation; every event of one element shares it.
    """

    __slots__ = ()


class TemplateEvent(namedtuple("TemplateEvent", "uid tag event handler")):
    """A handler deferred from an element inside a template.

    Attributes:
        uid (str): ``Uid`` that every template instance of the element keeps.
        tag (str): WPF type name, or ``{namespace}Name`` outside WPF.
    """

    __slots__ = ()


_WPF_NS = "http://schemas.microsoft.com/winfx/2006/xaml/presentation"
_XAML_NS = "http://schemas.microsoft.com/winfx/2006/xaml"
_HOOK_NS = (
    "clr-namespace:PyRevitLabs.PyRevit.Forms.Binding;"
    "assembly=pyRevitLabs.PyRevit.Forms.Binding"
)
_HOOK_ATTRIBUTE = "pyrevitevents:PythonEvents.Hook"
_POPUP_HOSTS = ("ContextMenu", "ToolTip")
_INITIAL_STATE_ATTRIBUTES = {
    "Checked": ("IsChecked",),
    "SelectionChanged": (
        "SelectedIndex",
        "SelectedItem",
        "SelectedValue",
        "IsSelected",
    ),
}
_EVENTS = (
    "Click",
    "TextChanged",
    "Checked",
    "Unchecked",
    "SelectionChanged",
    "MouseUp",
    "MouseDown",
    "MouseLeftButtonDown",
    "MouseLeftButtonUp",
    "MouseDoubleClick",
    "MouseEnter",
    "MouseLeave",
    "PreviewMouseLeftButtonDown",
    "PreviewMouseLeftButtonUp",
    "PreviewMouseRightButtonDown",
    "PreviewMouseMove",
    "PreviewMouseDoubleClick",
    "PreviewKeyUp",
    "MouseWheel",
    "PreviewMouseWheel",
    "PreviewKeyDown",
    "KeyDown",
    "KeyUp",
    "PreviewTextInput",
    "Loaded",
    "Closed",
    "Closing",
    "Activated",
    "Deactivated",
    "ContentRendered",
    "RequestNavigate",
    "ValueChanged",
    "SizeChanged",
    "IsVisibleChanged",
    "GotFocus",
    "LostFocus",
    "BeginningEdit",
    "DragOver",
    "DragLeave",
    "Drop",
    "PreviewDrop",
    "PreviewDragOver",
    "SelectedItemChanged",
    "SelectedCellsChanged",
    "Sorting",
    "Expanded",
)
_TEMPLATES = (
    "ControlTemplate",
    "DataTemplate",
    "HierarchicalDataTemplate",
    "ItemsPanelTemplate",
    "Style",
)
_NOT_ENTRY = object()
_MARKER = "pyRevitAttr{}".format(uuid.uuid4().hex)
_ATTRIBUTE_WHITESPACE = (
    ("\n", _MARKER + "LF", "&#10;"),
    ("\r", _MARKER + "CR", "&#13;"),
    ("\t", _MARKER + "TAB", "&#9;"),
)
_STATIC_RESOURCE = re.compile(r"^\{StaticResource\s+(?:ResourceKey=)?([^\s{}]+)\s*\}$")


def _children(element):
    return [node for node in element.childNodes if node.nodeType == node.ELEMENT_NODE]


def _serialize(document):
    """Write markup whose attribute line breaks survive WPF's XML parser.

    Python 3.12's minidom writes newlines and tabs inside attribute values
    literally, and XML attribute normalization then turns them into spaces.
    They are swapped for per-process ASCII markers, then for character
    references, so no authored text can collide with a marker.
    """
    for element in document.getElementsByTagName("*"):
        for name, value in list(element.attributes.items()):
            protected = value
            for character, marker, _ in _ATTRIBUTE_WHITESPACE:
                protected = protected.replace(character, marker)
            if protected != value:
                element.setAttribute(name, protected)
    markup = document.toxml()
    for _, marker, reference in _ATTRIBUTE_WHITESPACE:
        markup = markup.replace(marker, reference)
    return markup


def _wpf_prefix(root):
    """Return the prefix that names WPF types under ``root``, declaring one if absent."""
    if root.getAttribute("xmlns") == _WPF_NS:
        return ""
    for name, value in root.attributes.items():
        if name.startswith("xmlns:") and value == _WPF_NS:
            return name.split(":", 1)[1]
    root.setAttribute("xmlns:pyrevitwpf", _WPF_NS)
    return "pyrevitwpf"


def _merge_resources(document, sources):
    if not sources:
        return
    root = document.documentElement
    prefix = _wpf_prefix(root)

    def wpf_element(local_name):
        qualified = "{}:{}".format(prefix, local_name) if prefix else local_name
        return document.createElementNS(_WPF_NS, qualified)

    resource_tag = root.localName + ".Resources"
    resources = next(
        (node for node in _children(root) if node.localName == resource_tag), None
    )
    if resources is None:
        resources = document.createElementNS(
            root.namespaceURI, root.tagName + ".Resources"
        )
        root.insertBefore(resources, root.firstChild)
    dictionaries = [
        node for node in _children(resources) if node.localName == "ResourceDictionary"
    ]
    if dictionaries:
        dictionary = dictionaries[0]
    else:
        dictionary = wpf_element("ResourceDictionary")
        for node in list(resources.childNodes):
            dictionary.appendChild(node)
        resources.appendChild(dictionary)
    merge_tag = "ResourceDictionary.MergedDictionaries"
    merged = next(
        (node for node in _children(dictionary) if node.localName == merge_tag), None
    )
    if merged is None:
        merged = wpf_element(merge_tag)
        dictionary.insertBefore(merged, dictionary.firstChild)
    first_authored = merged.firstChild
    for source in sources:
        entry = wpf_element("ResourceDictionary")
        entry.setAttribute("Source", source)
        merged.insertBefore(entry, first_authored)


def _type_name(node):
    """Return a WPF element's type name, or ``{namespace}Name`` for other types."""
    if node.namespaceURI == _WPF_NS:
        return node.localName
    return "{{{}}}{}".format(node.namespaceURI, node.localName)


def _use_dynamic_resources(node, dynamic_keys):
    for attribute, value in list(node.attributes.items()):
        if ":" in attribute:
            continue
        match = _STATIC_RESOURCE.match(value.strip())
        if match and match.group(1) in dynamic_keys:
            node.setAttribute(
                attribute, "{{DynamicResource {}}}".format(match.group(1))
            )


def _ensure_name(document, node, names):
    name = node.getAttributeNS(_XAML_NS, "Name") or node.getAttribute("Name")
    if not name:
        name = "_pyrevit_auto_{}".format(len(names))
        node.setAttributeNS(_XAML_NS, "x:Name", name)
        document.documentElement.setAttribute("xmlns:x", _XAML_NS)
        names.append(name)
    return name


def _items_position(node, attributes, prefix):
    """Return the attribute index at which a selector's items exist, or None."""
    for child in _children(node):
        member = child.localName[len(prefix) :]
        if not child.localName.startswith(prefix) or member in ("Items", "ItemsSource"):
            return len(attributes)
    if "ItemsSource" in attributes:
        return attributes.index("ItemsSource")
    return None


def _replays_initial_state(node, attributes, event):
    """Return whether IronPython's loader would deliver ``event`` for initial state."""
    states = _INITIAL_STATE_ATTRIBUTES.get(event)
    if not states:
        return False
    position = attributes.index(event)
    prefix = node.localName + "."
    if any(
        child.localName.startswith(prefix) and child.localName[len(prefix) :] in states
        for child in _children(node)
    ):
        return True
    items = None
    if event == "SelectionChanged":
        items = _items_position(node, attributes, prefix)
    effective = [
        index if items is None else max(index, items)
        for index, name in enumerate(attributes)
        if name in states
    ]
    return not effective or max(effective) > position


def _root_properties(root):
    prefix = root.localName + "."
    names = set(
        name for name in root.attributes.keys() if ":" not in name and name != "xmlns"
    )
    names.update(
        child.localName[len(prefix) :]
        for child in _children(root)
        if child.localName.startswith(prefix)
    )
    return frozenset(names)


def _hook_template_source(document, node, token, index):
    key = node.getAttributeNS(_HOOK_NS, "PythonEvents.Hook")
    if not key:
        key = "{}:{}".format(token, index)
        document.documentElement.setAttribute("xmlns:pyrevitevents", _HOOK_NS)
        node.setAttributeNS(_HOOK_NS, _HOOK_ATTRIBUTE, key)
    return key


def _tag_template_source(node, index):
    uid = (
        node.getAttribute("Uid")
        or node.getAttributeNS(_XAML_NS, "Uid")
        or "_pyrevit_template_{}".format(index)
    )
    if node.hasAttributeNS(_XAML_NS, "Uid"):
        node.removeAttributeNS(_XAML_NS, "Uid")
    node.setAttribute("Uid", uid)
    return uid


def prepare_xaml(source, resource_sources, is_event=None, dynamic_keys=()):
    """Defer named events and prepend the host resource dictionaries.

    Args:
        source (str): Authored XAML markup.
        resource_sources (list[str]): Dictionary URIs merged ahead of the
            authored resources.
        is_event (callable, optional): ``is_event(type_name, attribute)``
            returns whether an attribute names a CLR event of that type. The
            CPython backend resolves WPF and ``clr-namespace`` types by
            reflection; ``_EVENTS`` is only the fallback for attributes it
            cannot resolve, and the whole list when ``is_event`` is omitted.
        dynamic_keys (collection, optional): Resource keys the host adds only
            after parsing. ``{StaticResource key}`` for them becomes
            ``{DynamicResource key}``, which resolves once they exist.

    Returns:
        PreparedXaml: Namespace declarations and markup extensions survive;
            an owner of a nested ``.Resources`` block is itself listed in
            ``resource_names`` when it sits inside a resource entry.

    Raises:
        ValueError: An adapted event has no named target. Unsupported XAML
            features are left for WPF to reject rather than silently stripped.
    """
    document = minidom.parseString(source)
    root = document.documentElement
    root_properties = _root_properties(root)
    names = []
    events = []
    resource_names = {}
    token = uuid.uuid4().hex

    def visit(
        node, in_template=False, resource=None, entry_owner=_NOT_ENTRY, in_popup=False
    ):
        in_template = in_template or node.localName in _TEMPLATES
        in_popup = in_popup or node.localName in _POPUP_HOSTS
        if entry_owner is not _NOT_ENTRY and not in_template:
            key = node.getAttributeNS(_XAML_NS, "Key") or node.getAttribute("x:Key")
            resource = (entry_owner, key) if key else None
        name = node.getAttributeNS(_XAML_NS, "Name") or node.getAttribute("Name")
        if dynamic_keys:
            _use_dynamic_resources(node, dynamic_keys)
        type_name = _type_name(node)
        attributes = list(node.attributes.keys())
        for event in attributes:
            if ":" in event or "." in event:
                continue
            if event not in _EVENTS and not (is_event and is_event(type_name, event)):
                continue
            handler = node.getAttribute(event)
            if in_template and in_popup:
                key = _hook_template_source(document, node, token, len(events))
                events.append(HookedEvent(key, event, handler))
            elif in_template:
                uid = _tag_template_source(node, len(events))
                events.append(TemplateEvent(uid, type_name, event, handler))
            else:
                name = _ensure_name(document, node, names)
                replay = _replays_initial_state(node, attributes, event)
                events.append(NamedEvent(name, event, handler, replay))
            node.removeAttribute(event)
        if name and not in_template:
            if name not in names:
                names.append(name)
            if resource is not None:
                resource_names[name] = resource
        for child in _children(node):
            if in_template or not child.localName.endswith(".Resources"):
                visit(child, in_template, resource, in_popup=in_popup)
                continue
            owner = None if node is root else _ensure_name(document, node, names)
            if owner is not None and resource is not None:
                resource_names.setdefault(owner, resource)
            for nested in _children(child):
                entries = (
                    _children(nested)
                    if nested.localName == "ResourceDictionary"
                    else [nested]
                )
                for entry in entries:
                    visit(entry, in_template, resource, owner, in_popup)

    visit(root)
    _merge_resources(document, resource_sources)
    return PreparedXaml(
        _serialize(document), names, events, resource_names, root_properties
    )
