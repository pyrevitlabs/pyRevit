"""Layout-based extension parser.

Reads extension_layout.yaml and *.panel.yaml files, resolves tool
references against a tool index, and builds the component tree that
uimaker.py consumes.
"""

import os
import os.path as op

from pyrevit import PYREVIT_APP_DIR
from pyrevit.coreutils import yaml
from pyrevit.coreutils.logger import get_logger
import pyrevit.extensions as exts
from pyrevit.extensions.components import Tab, Panel, GenericStack
from pyrevit.extensions.genericcomps import GenericUIComponent
from pyrevit.extensions.toolindex import make_layout_unique_name

# pylint: disable=W0703,C0302,C0103
mlogger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Layout entry grammar
#
# A panel's "layout" is a list of entries. Each entry is one of a small set
# of kinds. These helpers are the single source of truth for that wire format
# so the loader, the CLI generator (layout_cli), and the Layout Builder UI all
# read and write it identically; changing the format in one place updates all.
# ---------------------------------------------------------------------------

LAYOUT_ENTRY_SEPARATOR = "separator"
LAYOUT_ENTRY_SLIDEOUT = "slideout"
LAYOUT_ENTRY_STACK = "stack"
LAYOUT_ENTRY_TOOL = "tool"
LAYOUT_ENTRY_UNKNOWN = "unknown"


def classify_layout_entry(entry):
    """Classify a single raw entry from a panel's layout list.

    Args:
        entry: A raw YAML value from the layout list (str or dict).

    Returns:
        tuple[str, object]: (kind, payload) where kind is one of the
            LAYOUT_ENTRY_* constants:
                separator / slideout -> payload is None
                tool                 -> payload is the stripped tool name
                stack                -> payload is the raw child entry list
                unknown              -> payload is the original entry
    """
    if isinstance(entry, str):
        name = entry.strip()
        if name == exts.SEPARATOR_IDENTIFIER:
            return (LAYOUT_ENTRY_SEPARATOR, None)
        if name == exts.SLIDEOUT_IDENTIFIER:
            return (LAYOUT_ENTRY_SLIDEOUT, None)
        return (LAYOUT_ENTRY_TOOL, name)
    if isinstance(entry, dict) and exts.LAYOUT_STACK_KEY in entry:
        return (LAYOUT_ENTRY_STACK, entry[exts.LAYOUT_STACK_KEY])
    return (LAYOUT_ENTRY_UNKNOWN, entry)


def encode_separator_entry():
    """Wire-format layout entry for a separator."""
    return exts.SEPARATOR_IDENTIFIER


def encode_slideout_entry():
    """Wire-format layout entry for a slideout."""
    return exts.SLIDEOUT_IDENTIFIER


def encode_tool_entry(tool_name):
    """Wire-format layout entry for a tool reference."""
    return tool_name


def encode_stack_entry(child_entries):
    """Wire-format layout entry for a stack of already-encoded children."""
    return {exts.LAYOUT_STACK_KEY: child_entries}


def list_layout_presets(extension_dir):
    """List developer-provided layout presets in <ext>/layouts/.

    Each `*.layout.yaml` file in the extension's `layouts/` subfolder is
    treated as a named preset. The preset name is the filename with the
    `.layout.yaml` suffix stripped.

    Args:
        extension_dir (str): Path to the .extension directory

    Returns:
        list[tuple[str, str]]: Sorted list of (preset_name, file_path).
    """
    presets_dir = op.join(extension_dir, exts.LAYOUTS_DIR_NAME)
    if not op.isdir(presets_dir):
        return []

    presets = []
    suffix = exts.LAYOUT_PRESET_POSTFIX
    for entry in os.listdir(presets_dir):
        if entry.endswith(suffix):
            name = entry[:-len(suffix)]
            if name:
                presets.append((name, op.join(presets_dir, entry)))
    presets.sort(key=lambda p: p[0].lower())
    return presets


def has_layout_file(extension_dir):
    """Check if extension_layout.yaml exists in extension directory.

    Args:
        extension_dir (str): Path to the .extension directory

    Returns:
        bool: True if layout file found
    """
    return op.isfile(op.join(extension_dir, exts.EXT_LAYOUT_FILE))


def get_layout_cache_dir(extension_name):
    """Get the user-specific cache directory for custom layouts.

    Args:
        extension_name (str): Name of the extension (without .extension suffix)

    Returns:
        str: Path to <PYREVIT_APP_DIR>/Layouts/<extension_name>
    """
    return op.join(PYREVIT_APP_DIR, "Layouts", extension_name)


def get_custom_layout_file(extension_dir):
    """Resolve the user-configured custom layout override for an extension.

    Args:
        extension_dir (str): Path to the .extension directory

    Returns:
        str or None: Path to an existing custom layout file, or None.
    """
    try:
        from pyrevit.userconfig import user_config

        # Global toggle: skip custom layouts when disabled
        if user_config.disable_custom_layouts:
            return None
        ext_name = op.splitext(op.basename(extension_dir))[0]
        section_name = ext_name + exts.UI_EXTENSION_POSTFIX
        if user_config.has_section(section_name):
            section = user_config.get_section(section_name)
            custom_path = section.get_option("custom_layout_path", default_value="")
            if custom_path and op.isfile(custom_path):
                return custom_path
    except Exception as err:
        mlogger.debug(
            "Could not read custom layout config for %s: %s", extension_dir, err
        )
    return None


def get_bundled_layout_file(extension_dir):
    """Resolve the extension's bundled extension_layout.yaml, if present.

    Args:
        extension_dir (str): Path to the .extension directory

    Returns:
        str or None: Path to the bundled layout file, or None.
    """
    bundled = op.join(extension_dir, exts.EXT_LAYOUT_FILE)
    if op.isfile(bundled):
        return bundled
    return None


def get_layout_file(extension_dir):
    """Resolve which layout file to use for an extension.

    Resolution order:
        1. User config custom_layout_path for this extension (if file exists)
        2. extension_layout.yaml in extension root
        3. None (legacy mode)

    Args:
        extension_dir (str): Path to the .extension directory

    Returns:
        str or None: Path to the layout file, or None for legacy mode
    """
    return get_custom_layout_file(extension_dir) or get_bundled_layout_file(
        extension_dir
    )


def get_referenced_panel_files(layout_file):
    """Collect the panel layout_file references declared in a layout file.

    Args:
        layout_file (str): Path to an extension_layout.yaml file.

    Returns:
        list[str]: The layout_file values referenced by panels, in order and
            de-duplicated. Empty list if the file cannot be read.
    """
    try:
        layout_data = yaml.load_as_dict(layout_file)
    except Exception as err:
        mlogger.debug("Could not read layout file %s: %s", layout_file, err)
        return []

    refs = []
    if layout_data:
        for tab_data in layout_data.get(exts.LAYOUT_TABS_KEY, []) or []:
            for panel_data in tab_data.get(exts.LAYOUT_PANELS_KEY, []) or []:
                if isinstance(panel_data, dict):
                    ref = panel_data.get(exts.LAYOUT_FILE_KEY)
                    if ref and ref not in refs:
                        refs.append(ref)
    return refs


def parse_extension_layout(extension, tool_index, layout_file):
    """Parse layout file and build Tab/Panel/Tool tree on extension.

    Reads the layout YAML, creates Tab and Panel containers, resolves
    tool references from the tool index, and populates the extension's
    component tree.

    Args:
        extension: Extension object to populate
        tool_index (dict): Mapping of tool name to component object
        layout_file (str): Path to the extension_layout.yaml file

    Returns:
        bool: True if the layout produced at least one tab. False signals the
            caller to fall back to another layout file or to legacy parsing.
    """
    ext_dir = extension.directory
    ext_name = op.splitext(op.basename(ext_dir))[0]

    try:
        layout_data = yaml.load_as_dict(layout_file)
    except Exception as err:
        mlogger.error("Failed to read layout file %s: %s", layout_file, err)
        return False

    if not layout_data:
        mlogger.warning("Layout file is empty: %s", layout_file)
        return False

    tabs_data = layout_data.get(exts.LAYOUT_TABS_KEY, [])
    if not tabs_data:
        mlogger.warning("No tabs defined in layout file: %s", layout_file)
        return False

    layout_dir = op.dirname(layout_file)
    referenced_tools = set()
    tabs_added = 0

    for tab_data in tabs_data:
        tab = _create_tab(tab_data, ext_name, ext_dir)
        if tab is None:
            continue

        panels_data = tab_data.get(exts.LAYOUT_PANELS_KEY, [])
        for panel_data in panels_data:
            panel = _create_panel(
                panel_data, ext_name, ext_dir, tool_index, layout_dir, referenced_tools
            )
            if panel is not None:
                tab.add_component(panel)

        extension.add_component(tab)
        tabs_added += 1

    if not tabs_added:
        mlogger.warning("No valid tabs produced from layout file: %s", layout_file)
        return False

    # Attach tools not referenced in the layout as assembly-only commands.
    # They get compiled into the DLL but don't appear in the ribbon,
    # so layout changes don't require a new assembly build.
    unreferenced = [
        comp for name, comp in tool_index.items() if name not in referenced_tools
    ]
    if unreferenced:
        extension.set_assembly_only_commands(unreferenced)
        mlogger.debug(
            "Layout: %d tool(s) not in layout, included as assembly-only",
            len(unreferenced),
        )

    mlogger.debug(
        "Layout parsing complete for %s: %d tab(s)", ext_name, len(extension.components)
    )
    return True


def _coerce_bool(value):
    """Coerce a YAML scalar (native bool or string) to a bool."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() == "true"
    return False


def _apply_highlight(comp, data):
    """Apply the highlight directive from a layout entry to a component."""
    highlight = data.get(exts.MDATA_HIGHLIGHT_KEY)
    if highlight and isinstance(highlight, str):
        comp.highlight_type = highlight.lower()


def _apply_panel_metadata(panel, data):
    """Apply panel presentation metadata from a layout entry.

    Mirrors the bundle.yaml keys the legacy parser honors so a panel keeps
    its appearance when defined in (or migrated to) a layout file.
    """
    _apply_highlight(panel, data)
    panel.collapsed = _coerce_bool(data.get(exts.MDATA_COLLAPSED_KEY))
    panel.is_beta = _coerce_bool(data.get(exts.MDATA_BETA_SCRIPT))

    background = data.get(exts.MDATA_BACKGROUND_KEY)
    if isinstance(background, dict):
        panel.title_background = background.get(exts.MDATA_BACKGROUND_TITLE_KEY)
        panel.slideout_background = background.get(exts.MDATA_BACKGROUND_SLIDEOUT_KEY)
        panel.panel_background = background.get(exts.MDATA_BACKGROUND_PANEL_KEY)
    elif isinstance(background, str):
        panel.panel_background = background


def _create_tab(tab_data, ext_name, ext_dir):
    """Create a Tab component from layout YAML data."""
    tab_name = tab_data.get(exts.LAYOUT_NAME_KEY)
    if not tab_name:
        mlogger.error('Tab definition missing "name" key')
        return None

    tab = Tab(cmp_path=None)
    tab.name = tab_name
    tab._ui_title = tab_data.get(exts.LAYOUT_TITLE_KEY, tab_name)
    tab.unique_name = make_layout_unique_name(ext_name, tab_name)
    _apply_highlight(tab, tab_data)

    mlogger.debug("Created layout tab: %s", tab_name)
    return tab


def _create_panel(
    panel_data, ext_name, ext_dir, tool_index, layout_dir=None, referenced_tools=None
):
    """Create a Panel component from layout YAML data.

    Handles both inline layout and external panel.yaml file references.

    Args:
        panel_data (dict): Panel definition from YAML (dict with name, layout/layout_file)
        ext_name (str): Extension name
        ext_dir (str): Extension directory path
        tool_index (dict): Tool name to component mapping
        layout_dir (str): Directory of the active layout file (for custom cached layouts)
        referenced_tools (set): Set to track tool names placed in the layout

    Returns:
        Panel or None: Created panel component
    """
    if layout_dir is None:
        layout_dir = ext_dir

    # Resolve the source dict that carries this panel's title, presentation
    # metadata, and layout. For inline panels that is the entry itself; for
    # string/layout_file references it is the external .panel.yaml.
    if isinstance(panel_data, str):
        panel_name = panel_data
        source = _load_panel_file_dict(
            panel_name + exts.PANEL_LAYOUT_POSTFIX, ext_dir, layout_dir
        )
        panel_title = source.get(exts.LAYOUT_TITLE_KEY, panel_name)
    elif isinstance(panel_data, dict):
        panel_name = panel_data.get(exts.LAYOUT_NAME_KEY)
        if not panel_name:
            mlogger.error('Panel definition missing "name" key')
            return None

        layout_file_ref = panel_data.get(exts.LAYOUT_FILE_KEY)
        if layout_file_ref:
            source = _load_panel_file_dict(layout_file_ref, ext_dir, layout_dir)
            # An explicit title on the outer entry wins over the file's.
            panel_title = panel_data.get(exts.LAYOUT_TITLE_KEY) or source.get(
                exts.LAYOUT_TITLE_KEY, panel_name
            )
        else:
            source = panel_data
            panel_title = panel_data.get(exts.LAYOUT_TITLE_KEY, panel_name)
    else:
        mlogger.error("Invalid panel definition type: %s", type(panel_data))
        return None

    panel = Panel(cmp_path=None)
    panel.name = panel_name
    panel._ui_title = panel_title
    panel.unique_name = make_layout_unique_name(ext_name, panel_name)
    _apply_panel_metadata(panel, source)

    layout_list = source.get(exts.LAYOUT_KEY, [])
    if layout_list:
        _populate_panel(panel, layout_list, tool_index, ext_name, referenced_tools)

    mlogger.debug(
        "Created layout panel: %s with %d component(s)",
        panel_name,
        len(panel.components),
    )
    return panel


def _load_panel_file_dict(filename, ext_dir, layout_dir=None):
    """Load a panel definition dict from a .panel.yaml file.

    Checks layout_dir first (for custom cached layouts), then ext_dir.

    Args:
        filename (str): Panel file name (e.g. "Edit.panel.yaml")
        ext_dir (str): Extension directory path
        layout_dir (str): Directory of the active layout file

    Returns:
        dict: Parsed panel file (title/metadata/layout), or {} if not found.
    """
    for base in (layout_dir, ext_dir):
        if not base:
            continue
        filepath = op.join(base, filename)
        if op.isfile(filepath):
            try:
                return yaml.load_as_dict(filepath) or {}
            except Exception as err:
                mlogger.error(
                    "Failed to read panel layout file %s: %s", filepath, err
                )
                return {}

    mlogger.debug("Panel layout file not found: %s", filename)
    return {}


def _populate_panel(panel, layout_list, tool_index, ext_name, referenced_tools=None):
    """Populate a panel with components based on layout list.

    Resolves each layout entry to either a tool from the index,
    a stack grouping, or a separator/slideout directive.

    Args:
        panel: Panel component to populate
        layout_list (list): Layout entries from YAML
        tool_index (dict): Tool name to component mapping
        ext_name (str): Extension name for unique name generation
        referenced_tools (set): Set to track tool names placed in the layout
    """
    stack_counter = 0

    for entry in layout_list:
        kind, payload = classify_layout_entry(entry)
        if kind == LAYOUT_ENTRY_SEPARATOR:
            panel.add_component(_make_marker(exts.SEPARATOR_IDENTIFIER))
        elif kind == LAYOUT_ENTRY_SLIDEOUT:
            panel.add_component(_make_marker(exts.SLIDEOUT_IDENTIFIER))
        elif kind == LAYOUT_ENTRY_TOOL:
            _place_tool(payload, panel, tool_index, referenced_tools)
        elif kind == LAYOUT_ENTRY_STACK:
            _create_stack(
                payload, panel, tool_index, ext_name, stack_counter, referenced_tools
            )
            stack_counter += 1
        else:
            mlogger.warning("Unknown layout entry (%s): %s", type(entry), entry)


def _make_marker(identifier):
    """Create a separator/slideout marker component."""
    marker = GenericUIComponent()
    marker.type_id = identifier
    marker.name = identifier
    return marker


def _place_tool(tool_name, parent, tool_index, referenced_tools=None):
    """Resolve a tool name against the index and add it to the parent.

    Args:
        tool_name (str): Tool name referenced in the layout
        parent: Parent container to add the resolved component to
        tool_index (dict): Tool name to component mapping
        referenced_tools (set): Set to track tool names placed in the layout

    Returns:
        bool: True if the tool was found and placed.
    """
    if tool_name not in tool_index:
        mlogger.warning(
            'Tool "%s" referenced in layout but not found in tool index', tool_name
        )
        return False

    # A tool is one compiled command; placing the same instance in two
    # locations would corrupt its parent/control id. Each tool may appear once.
    if referenced_tools is not None and tool_name in referenced_tools:
        mlogger.warning(
            'Tool "%s" is referenced more than once in the layout; '
            "a tool can appear in only one location. Ignoring the duplicate.",
            tool_name,
        )
        return False

    parent.add_component(tool_index[tool_name])
    if referenced_tools is not None:
        referenced_tools.add(tool_name)
    return True


def _create_stack(
    children_names, panel, tool_index, ext_name, stack_idx, referenced_tools=None
):
    """Create a GenericStack with children from tool index.

    Args:
        children_names (list): List of tool name strings
        panel: Parent panel to add stack to
        tool_index (dict): Tool name to component mapping
        ext_name (str): Extension name
        stack_idx (int): Stack counter for unique name generation
        referenced_tools (set): Set to track tool names placed in the layout
    """
    stack_name = "_stack_%d" % stack_idx
    stack = GenericStack(cmp_path=None)
    stack.name = stack_name
    panel_name_part = panel.name.replace(" ", "")
    stack.unique_name = make_layout_unique_name(
        ext_name,
        panel_name_part + exts.UNIQUE_ID_SEPARATOR + stack_name,
    )

    for child in children_names:
        kind, payload = classify_layout_entry(child)
        if kind == LAYOUT_ENTRY_TOOL:
            _place_tool(payload, stack, tool_index, referenced_tools)
        else:
            mlogger.warning("Stack child must be a tool name, got: %s", child)

    if stack.components:
        panel.add_component(stack)
    else:
        mlogger.warning("Stack %s has no valid children, skipping", stack_name)
