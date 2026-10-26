"""Prepare trusted dialog XAML for pythonnet without losing namespace prefixes.

Common control events are deferred until the native tree exists. Templates
retain their own namescopes and use routed handlers on the root window.
"""

from xml.dom import minidom


_WPF_NS = "http://schemas.microsoft.com/winfx/2006/xaml/presentation"
_XAML_NS = "http://schemas.microsoft.com/winfx/2006/xaml"
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
_TEMPLATES = ("ControlTemplate", "DataTemplate", "ItemsPanelTemplate", "Style")


def _children(element):
    return [node for node in element.childNodes if node.nodeType == node.ELEMENT_NODE]


def _merge_resources(document, sources):
    if not sources:
        return
    root = document.documentElement
    resource_tag = root.localName + ".Resources"
    resources = next(
        (node for node in _children(root) if node.localName == resource_tag), None
    )
    if resources is None:
        resources = document.createElementNS(_WPF_NS, resource_tag)
        root.insertBefore(resources, root.firstChild)
    dictionaries = [
        node for node in _children(resources) if node.localName == "ResourceDictionary"
    ]
    if dictionaries:
        dictionary = dictionaries[0]
    else:
        dictionary = document.createElementNS(_WPF_NS, "ResourceDictionary")
        for node in list(resources.childNodes):
            dictionary.appendChild(node)
        resources.appendChild(dictionary)
    merge_tag = "ResourceDictionary.MergedDictionaries"
    merged = next(
        (node for node in _children(dictionary) if node.localName == merge_tag), None
    )
    if merged is None:
        merged = document.createElementNS(_WPF_NS, merge_tag)
        dictionary.insertBefore(merged, dictionary.firstChild)
    first_authored = merged.firstChild
    for source in sources:
        entry = document.createElementNS(_WPF_NS, "ResourceDictionary")
        entry.setAttribute("Source", source)
        merged.insertBefore(entry, first_authored)


def prepare_xaml(source, resource_sources):
    """Defer supported named events and prepend the host resource dictionaries.

    Returns:
        tuple[str, list[str], list[tuple[str, str, str]]]: Markup, root-namescope
            control names and deferred (name, event, handler) registrations.
            Namespace declarations and markup extensions survive.

    Raises:
        ValueError: An adapted event has no named target. Unsupported XAML
            features are left for WPF to reject rather than silently stripped.
    """
    document = minidom.parseString(source)
    names = []
    events = []

    def visit(node, in_template=False):
        in_template = in_template or node.localName in _TEMPLATES
        name = node.getAttributeNS(_XAML_NS, "Name") or node.getAttribute("Name")
        for event in _EVENTS:
            if node.hasAttribute(event):
                if in_template:
                    target = "@template:" + node.localName
                else:
                    if not name:
                        name = "_pyrevit_auto_{}".format(len(names))
                        node.setAttributeNS(_XAML_NS, "x:Name", name)
                        document.documentElement.setAttribute("xmlns:x", _XAML_NS)
                    target = name
                events.append((target, event, node.getAttribute(event)))
                node.removeAttribute(event)
        if name and not in_template:
            names.append(name)
        for child in _children(node):
            visit(child, in_template)

    visit(document.documentElement)
    _merge_resources(document, resource_sources)
    return document.toxml(), names, events
