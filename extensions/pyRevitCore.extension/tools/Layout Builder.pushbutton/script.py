# pylint: disable=E0401,C0103,W0603
"""Visual editor for extension ribbon layouts.

Opens a WPF window with two columns:
- Left: searchable list of available tools in the selected extension
- Right: tree view of the layout structure (Tabs > Panels > items)

Users can insert tools, create structure elements (Tab, Panel, Stack,
Separator, Slideout), move/remove items, and save to extension_layout.yaml.
"""

import os
import os.path as op
from collections import OrderedDict

from pyrevit import script, forms
from pyrevit.coreutils import yaml as pyyaml
from pyrevit.framework import ObservableCollection
from pyrevit.extensions.layout_parser import has_layout_file, list_layout_presets
from pyrevit.extensions.toolindex import build_tool_index
from pyrevit.loader import sessionmgr
import pyrevit.extensions as exts

mlogger = script.get_logger()

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


class LayoutNode(forms.Reactive):
    """A node in the layout tree (tab, panel, stack, tool, separator, etc.)."""

    def __init__(self, node_type, name="", title="", children=None):
        self._node_type = node_type
        self._name = name
        self._title = title
        self._missing = False
        self._children = ObservableCollection[object]()
        self.parent = None
        if children:
            for child in children:
                self.add_child(child)

    @forms.reactive
    def node_type(self):
        return self._node_type

    @forms.reactive
    def is_missing(self):
        return self._missing

    @is_missing.setter
    def is_missing(self, value):
        self._missing = value
        self.OnPropertyChanged("is_missing")
        self.OnPropertyChanged("display_name")

    @forms.reactive
    def display_name(self):
        if self._node_type in ("separator", "slideout"):
            return ""
        label = self._title or self._name
        if self._missing:
            label += "  [missing]"
        return label

    @forms.reactive
    def type_badge(self):
        return self._node_type.upper()

    @property
    def name(self):
        return self._name

    @property
    def title(self):
        return self._title

    @property
    def children(self):
        return self._children

    def add_child(self, child):
        child.parent = self
        self._children.Add(child)

    def insert_child(self, index, child):
        child.parent = self
        self._children.Insert(index, child)

    def remove_child(self, child):
        child.parent = None
        self._children.Remove(child)

    @property
    def is_container(self):
        return self._node_type in ("tab", "panel", "stack")

    def collect_tool_names(self):
        """Recursively collect all tool names placed in this subtree."""
        names = set()
        if self._node_type == "tool":
            names.add(self._name)
        for child in self._children:
            names.update(child.collect_tool_names())
        return names


class ToolItem(forms.Reactive):
    """An available tool shown in the left-hand list."""

    def __init__(self, name, tool_type):
        self._name = name
        self._tool_type = tool_type
        self._placed = False

    @forms.reactive
    def display(self):
        label = "{} ({})".format(self._name, self._tool_type)
        if self._placed:
            label += "  [placed]"
        return label

    @property
    def name(self):
        return self._name

    @property
    def placed(self):
        return self._placed

    @placed.setter
    def placed(self, value):
        self._placed = value
        self.OnPropertyChanged("display")


# ---------------------------------------------------------------------------
# YAML <-> LayoutNode conversion
# ---------------------------------------------------------------------------


def _layout_entry_to_node(entry):
    """Convert a single layout YAML entry to a LayoutNode."""
    if isinstance(entry, str):
        if entry == exts.SEPARATOR_IDENTIFIER:
            return LayoutNode("separator")
        if entry == exts.SLIDEOUT_IDENTIFIER:
            return LayoutNode("slideout")
        return LayoutNode("tool", name=entry)
    if isinstance(entry, dict):
        if exts.LAYOUT_STACK_KEY in entry:
            children = [_layout_entry_to_node(e) for e in entry[exts.LAYOUT_STACK_KEY]]
            return LayoutNode("stack", children=children)
    return None


def load_layout_tree(layout_file, extension_dir):
    """Parse extension_layout.yaml into a list of root LayoutNode (tabs)."""
    data = pyyaml.load_as_dict(layout_file)
    if not data or exts.LAYOUT_TABS_KEY not in data:
        return []

    roots = []
    for tab_data in data[exts.LAYOUT_TABS_KEY]:
        tab_name = tab_data.get(exts.LAYOUT_NAME_KEY, "")
        tab_title = tab_data.get(exts.LAYOUT_TITLE_KEY, "")
        tab_node = LayoutNode("tab", name=tab_name, title=tab_title)

        for panel_data in tab_data.get(exts.LAYOUT_PANELS_KEY, []):
            panel_name = panel_data.get(exts.LAYOUT_NAME_KEY, "")
            panel_title = panel_data.get(exts.LAYOUT_TITLE_KEY, "")
            panel_node = LayoutNode("panel", name=panel_name, title=panel_title)

            layout_items = panel_data.get(exts.LAYOUT_KEY, [])
            # If panel uses external layout_file, load it
            if not layout_items:
                panel_file = panel_data.get(exts.LAYOUT_FILE_KEY, "")
                if panel_file:
                    panel_path = op.join(extension_dir, panel_file)
                    if op.isfile(panel_path):
                        pdata = pyyaml.load_as_dict(panel_path)
                        layout_items = pdata.get(exts.LAYOUT_KEY, [])
                        if not panel_title:
                            panel_title = pdata.get(exts.LAYOUT_TITLE_KEY, "")
                            panel_node._title = panel_title

            for entry in layout_items:
                node = _layout_entry_to_node(entry)
                if node:
                    panel_node.add_child(node)

            tab_node.add_child(panel_node)
        roots.append(tab_node)
    return roots


def tree_to_yaml_dict(roots):
    """Convert list of root LayoutNode (tabs) back to a YAML-serializable dict."""
    tabs_data = []
    for tab in roots:
        tab_entry = OrderedDict()
        tab_entry["name"] = tab.name
        if tab.title and tab.title != tab.name:
            tab_entry["title"] = tab.title

        panels_data = []
        for panel in tab.children:
            panel_entry = OrderedDict()
            panel_entry["name"] = panel.name
            if panel.title and panel.title != panel.name:
                panel_entry["title"] = panel.title

            layout_list = []
            for item in panel.children:
                layout_list.append(_node_to_layout_entry(item))
            if layout_list:
                panel_entry["layout"] = layout_list
            panels_data.append(panel_entry)

        if panels_data:
            tab_entry["panels"] = panels_data
        tabs_data.append(tab_entry)

    return OrderedDict([("tabs", tabs_data)])


def _node_to_layout_entry(node):
    """Convert a LayoutNode to a YAML layout entry."""
    if node.node_type == "separator":
        return exts.SEPARATOR_IDENTIFIER
    if node.node_type == "slideout":
        return exts.SLIDEOUT_IDENTIFIER
    if node.node_type == "tool":
        return node.name
    if node.node_type == "stack":
        children = [_node_to_layout_entry(c) for c in node.children]
        return {"stack": children}
    return node.name


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

# Mapping: parent node_type -> allowed child node_types
ALLOWED_CHILDREN = {
    "tab": {"panel"},
    "panel": {"tool", "stack", "separator", "slideout"},
    "stack": {"tool"},
}


def can_insert_into(parent_type, child_type):
    """Check if child_type can be placed inside parent_type."""
    allowed = ALLOWED_CHILDREN.get(parent_type, set())
    return child_type in allowed


def _find_container_for(target_node, child_type):
    """Given a selected target node, find the right parent and index to insert.

    If target is a valid container for child_type, insert as last child.
    Otherwise insert after target in its parent.
    Returns (parent_node, insert_index) or (None, None) if invalid.
    """
    if can_insert_into(target_node.node_type, child_type):
        return target_node, target_node.children.Count
    # Try inserting after target in its parent
    parent = target_node.parent
    if parent and can_insert_into(parent.node_type, child_type):
        idx = list(parent.children).index(target_node)
        return parent, idx + 1
    return None, None


# ---------------------------------------------------------------------------
# Custom layout storage
# ---------------------------------------------------------------------------

APPDATA_DIR = os.environ.get("APPDATA", op.expanduser("~"))


def _get_layout_cache_dir(extension_name):
    """Get the user-specific cache directory for custom layouts.

    Follows the same convention as Settings: %APPDATA%/pyRevit/Layouts/<Name>/
    """
    return op.join(APPDATA_DIR, "pyRevit", "Layouts", extension_name)


def _set_custom_layout_config(extension_name, layout_path):
    """Set custom_layout_path in user config for the given extension."""
    from pyrevit.userconfig import user_config

    section_name = extension_name + exts.UI_EXTENSION_POSTFIX
    if not user_config.has_section(section_name):
        user_config.add_section(section_name)
    section = user_config.get_section(section_name)
    section.custom_layout_path = layout_path
    user_config.save_changes()


def _get_custom_layout_path(extension_name):
    """Get custom layout path from user config, if set and valid."""
    try:
        from pyrevit.userconfig import user_config

        if user_config.disable_custom_layouts:
            return None
        section_name = extension_name + exts.UI_EXTENSION_POSTFIX
        if user_config.has_section(section_name):
            section = user_config.get_section(section_name)
            path = section.get_option("custom_layout_path", default_value="")
            if path and op.isfile(path):
                return path
    except Exception as err:
        mlogger.debug(
            "Could not read custom layout config for %s: %s", extension_name, err
        )
    return None


# ---------------------------------------------------------------------------
# WPF Window
# ---------------------------------------------------------------------------


class LayoutBuilderWindow(forms.WPFWindow):
    """Main layout builder window."""

    def __init__(self, extension_dir, extension_name, tool_index, roots):
        forms.WPFWindow.__init__(self, "LayoutBuilderWindow.xaml")
        self._extension_dir = extension_dir
        self._extension_name = extension_name
        self._tool_index = tool_index
        self._roots = ObservableCollection[object]()

        # Populate tree roots
        for r in roots:
            self._roots.Add(r)
        self.layout_tv.ItemsSource = self._roots

        # Build tool list
        self._all_tools = []
        for name, comp in sorted(tool_index.items()):
            ctype = type(comp).__name__
            self._all_tools.append(ToolItem(name, ctype))

        self._show_all = False
        self._update_missing_flags()
        self._update_placed_flags()
        self._apply_tool_filter("")

        self.header_tb.Text = "Layout Builder - {}".format(extension_name)

        # Show the Load Preset button only when the extension ships presets
        self._presets = list_layout_presets(extension_dir)
        if not self._presets:
            from pyrevit.framework import Windows
            self.load_preset_btn.Visibility = Windows.Visibility.Collapsed

    def _update_missing_flags(self):
        """Flag tool nodes that reference tools not in the index."""

        def _walk(node):
            if node.node_type == "tool":
                node.is_missing = node.name not in self._tool_index
            for child in node.children:
                _walk(child)

        for root in self._roots:
            _walk(root)

    def _update_placed_flags(self):
        """Mark tools that are already placed in the layout."""
        placed_names = set()
        for root in self._roots:
            placed_names.update(root.collect_tool_names())
        for tool in self._all_tools:
            tool.placed = tool.name in placed_names
        self._update_missing_flags()
        self._apply_tool_filter(self.search_tb.Text)

    def _apply_tool_filter(self, search_text):
        search_lower = search_text.lower()
        filtered = [t for t in self._all_tools if search_lower in t.name.lower()]
        if not self._show_all:
            filtered = [t for t in filtered if not t.placed]
        self.tools_lb.ItemsSource = ObservableCollection[object](filtered)

    def search_changed(self, sender, args):
        self._apply_tool_filter(self.search_tb.Text)

    def load_preset(self, sender, args):
        """Load a developer-provided preset from <ext>/layouts/.

        Replaces the current tree. Confirms first if the tree is non-empty
        so a user editing a layout doesn't lose their work by accident.
        """
        if not self._presets:
            forms.alert("No layout presets found in this extension.")
            return

        preset_names = [name for name, _ in self._presets]
        choice = forms.SelectFromList.show(
            preset_names,
            title="Load Layout Preset",
            multiselect=False
        )
        if not choice:
            return

        if self._roots.Count > 0:
            if not forms.alert(
                "Loading a preset will replace the current layout. Continue?",
                yes=True, no=True
            ):
                return

        preset_path = dict(self._presets)[choice]
        new_roots = load_layout_tree(preset_path, self._extension_dir)

        self._roots.Clear()
        for r in new_roots:
            self._roots.Add(r)
        self._update_placed_flags()

    def toggle_show_all(self, sender, args):
        self._show_all = not self._show_all
        self.show_all_btn.Content = "Hide Placed" if self._show_all else "Show All"
        self._apply_tool_filter(self.search_tb.Text)

    def insert_tool(self, sender, args):
        """Insert selected tool into layout tree."""
        tool_item = self.tools_lb.SelectedItem
        if not tool_item:
            forms.alert("Select a tool from the list first.")
            return

        target = self.layout_tv.SelectedItem
        if not target:
            forms.alert("Select a location in the layout tree first.")
            return

        parent, idx = _find_container_for(target, "tool")
        if parent is None:
            forms.alert(
                "Cannot insert a tool here.\n"
                "Tools can be placed inside Panels or Stacks."
            )
            return

        new_node = LayoutNode("tool", name=tool_item.name)
        parent.insert_child(idx, new_node)
        self._update_placed_flags()

    def add_tab(self, sender, args):
        name = forms.ask_for_string(prompt="Tab name:", title="Add Tab")
        if name:
            node = LayoutNode("tab", name=name)
            self._roots.Add(node)

    def add_panel(self, sender, args):
        target = self.layout_tv.SelectedItem
        if not target:
            forms.alert("Select a Tab to add the Panel to.")
            return

        # Find the tab (target itself or its parent chain)
        tab = target if target.node_type == "tab" else None
        if not tab and target.parent and target.parent.node_type == "tab":
            tab = target.parent
        if not tab:
            forms.alert("Select a Tab (or an item inside a Tab) first.")
            return

        name = forms.ask_for_string(prompt="Panel name:", title="Add Panel")
        if name:
            node = LayoutNode("panel", name=name)
            tab.add_child(node)

    def add_stack(self, sender, args):
        target = self.layout_tv.SelectedItem
        if not target:
            forms.alert("Select a Panel to add the Stack to.")
            return

        parent, idx = _find_container_for(target, "stack")
        if parent is None:
            # stack goes into panel - try harder
            if target.node_type == "panel":
                parent, idx = target, target.children.Count
            else:
                forms.alert("Stacks can only be placed inside Panels.")
                return

        node = LayoutNode("stack")
        parent.insert_child(idx, node)

    def add_separator(self, sender, args):
        target = self.layout_tv.SelectedItem
        if not target:
            forms.alert("Select a Panel to add the Separator to.")
            return

        parent, idx = _find_container_for(target, "separator")
        if parent is None:
            forms.alert("Separators can only be placed inside Panels.")
            return

        node = LayoutNode("separator")
        parent.insert_child(idx, node)

    def add_slideout(self, sender, args):
        target = self.layout_tv.SelectedItem
        if not target:
            forms.alert("Select a Panel to add the Slideout to.")
            return

        # Find the target panel
        panel = None
        if target.node_type == "panel":
            panel = target
        elif target.parent and target.parent.node_type == "panel":
            panel = target.parent

        if not panel:
            forms.alert("Slideouts can only be placed inside Panels.")
            return

        # Check for existing slideout
        for child in panel.children:
            if child.node_type == "slideout":
                forms.alert("This panel already has a slideout.")
                return

        parent, idx = _find_container_for(target, "slideout")
        if parent is None:
            forms.alert("Slideouts can only be placed inside Panels.")
            return

        node = LayoutNode("slideout")
        parent.insert_child(idx, node)

    def _select_tree_item(self, data_item):
        """Re-select a data item in the TreeView after a collection change."""
        container = self._find_tree_container(self.layout_tv, data_item)
        if container:
            container.IsSelected = True
            container.BringIntoView()

    def _find_tree_container(self, parent, data_item):
        """Walk the TreeView visual tree to find the TreeViewItem for data_item."""
        if parent is None:
            return None
        generator = parent.ItemContainerGenerator
        for i in range(generator.Items.Count):
            container = generator.ContainerFromIndex(i)
            if container is None:
                continue
            if container.DataContext == data_item:
                return container
            # Recurse into children
            child_result = self._find_tree_container(container, data_item)
            if child_result:
                return child_result
        return None

    def move_up(self, sender, args):
        selected = self.layout_tv.SelectedItem
        if not selected:
            return
        parent = selected.parent
        if parent:
            siblings = parent.children
        else:
            siblings = self._roots

        idx = list(siblings).index(selected)
        if idx > 0:
            siblings.RemoveAt(idx)
            siblings.Insert(idx - 1, selected)
            self._select_tree_item(selected)

    def move_down(self, sender, args):
        selected = self.layout_tv.SelectedItem
        if not selected:
            return
        parent = selected.parent
        if parent:
            siblings = parent.children
        else:
            siblings = self._roots

        idx = list(siblings).index(selected)
        if idx < siblings.Count - 1:
            siblings.RemoveAt(idx)
            siblings.Insert(idx + 1, selected)
            self._select_tree_item(selected)

    def remove_node(self, sender, args):
        selected = self.layout_tv.SelectedItem
        if not selected:
            return
        parent = selected.parent
        if parent:
            parent.remove_child(selected)
        else:
            self._roots.Remove(selected)
        self._update_placed_flags()

    def save_click(self, sender, args):
        roots = list(self._roots)
        if not roots:
            forms.alert("Layout is empty. Add at least one Tab.")
            return

        # Validate
        warnings = []
        missing_names = []

        def _collect_missing(node):
            if node.node_type == "tool" and node.is_missing:
                missing_names.append(node.name)
            for child in node.children:
                _collect_missing(child)

        for tab in roots:
            _collect_missing(tab)
            if not tab.children or tab.children.Count == 0:
                warnings.append("Tab '{}' has no panels.".format(tab.name))
            for panel in tab.children:
                for item in panel.children:
                    if item.node_type == "stack":
                        count = item.children.Count
                        if count < 2 or count > 3:
                            warnings.append(
                                "Stack in panel '{}' has {} items "
                                "(recommended 2-3).".format(panel.name, count)
                            )
        if missing_names:
            warnings.append(
                "Missing tools (will not appear in ribbon): {}".format(
                    ", ".join(missing_names)
                )
            )

        if warnings:
            msg = "Warnings:\n" + "\n".join(warnings) + "\n\nSave anyway?"
            if not forms.alert(msg, yes=True, no=True):
                return

        # Save as custom user layout (not overwriting extension source)
        data = tree_to_yaml_dict(roots)

        cache_dir = _get_layout_cache_dir(self._extension_name)
        if not op.isdir(cache_dir):
            os.makedirs(cache_dir)

        layout_path = op.join(cache_dir, exts.EXT_LAYOUT_FILE)
        pyyaml.dump_dict(data, layout_path)

        # Point user config to the cached layout
        _set_custom_layout_config(self._extension_name, layout_path)

        forms.alert(
            "Custom layout saved to:\n{}\n\n"
            "pyRevit will now reload to apply changes.".format(layout_path),
            title="Saved",
        )
        self.Close()
        sessionmgr.reload_pyrevit()

    def cancel_click(self, sender, args):
        self.Close()


# ---------------------------------------------------------------------------
# Extension selection (entry point)
# ---------------------------------------------------------------------------

# Find extensions root
# __file__ is at: extensions/<ext>.extension/tools/<bundle>.pushbutton/script.py
# 4 dirname calls from __file__ reaches the extensions/ directory
extensions_dir = op.dirname(op.dirname(op.dirname(op.dirname(op.abspath(__file__)))))

# Also check user extensions from pyRevit config
ext_dirs = []
if op.isdir(extensions_dir):
    for entry in os.listdir(extensions_dir):
        ext_path = op.join(extensions_dir, entry)
        if entry.endswith(exts.UI_EXTENSION_POSTFIX) and op.isdir(ext_path):
            ext_dirs.append(ext_path)

if not ext_dirs:
    forms.alert("No extensions found!")
    script.exit()

# Let user pick an extension
ext_names = [op.basename(d) for d in ext_dirs]
selected = forms.SelectFromList.show(
    ext_names, title="Select Extension to Edit", multiselect=False
)
if not selected:
    script.exit()

selected_dir = ext_dirs[ext_names.index(selected)]
selected_name = op.splitext(selected)[0]

# Build tool index
tools_dir = op.join(selected_dir, exts.TOOLS_DIR_NAME)
tool_index = build_tool_index(tools_dir, selected_dir)

# Load existing layout or start empty
# Priority: custom user layout > bundled extension layout > empty
custom_layout = _get_custom_layout_path(selected_name)
if custom_layout:
    roots = load_layout_tree(custom_layout, selected_dir)
elif has_layout_file(selected_dir):
    layout_file = op.join(selected_dir, exts.EXT_LAYOUT_FILE)
    if op.isfile(layout_file):
        roots = load_layout_tree(layout_file, selected_dir)
    else:
        roots = []
else:
    roots = []

# Show the builder window
window = LayoutBuilderWindow(selected_dir, selected_name, tool_index, roots)
window.show_dialog()
