"""CLI utilities for layout-based extension management.

Provides commands to:
- Generate layout YAML from an existing legacy extension
- List all tools in an extension (layout or legacy mode)

These can be invoked as developer pushbutton scripts in Revit,
or called programmatically.
"""

import os.path as op
from collections import OrderedDict

from pyrevit.coreutils import yaml as pyyaml
from pyrevit.coreutils.logger import get_logger
import pyrevit.extensions as exts
from pyrevit.extensions import layout_parser

# pylint: disable=W0703,C0302,C0103
mlogger = get_logger(__name__)


def generate_layout(extension_dir, output_dir=None, split_panels=False):
    """Generate extension_layout.yaml and panel.yaml files from a legacy extension.

    Parses the extension using the legacy directory-walking parser, then
    produces YAML layout files that would recreate the same UI structure.

    Args:
        extension_dir (str): Path to the .extension directory
        output_dir (str, optional): Where to write output files.
            Defaults to the extension directory itself.
        split_panels (bool): If True, write complex panels to separate
            .panel.yaml files. If False (default), inline all layouts
            into extension_layout.yaml.

    Returns:
        list: Paths to generated files
    """
    from pyrevit.extensions.components import Extension
    from pyrevit.extensions.parser import _parse_for_components

    if output_dir is None:
        output_dir = extension_dir

    # Parse extension using legacy parser
    extension = Extension(cmp_path=extension_dir)
    _parse_for_components(extension)

    if not extension.components:
        mlogger.warning("No components found in extension: %s", extension_dir)
        return []

    generated_files = []
    used_panel_filenames = set()

    # Build the extension_layout.yaml content
    tabs_data = []
    for tab in extension.components:
        tab_entry = OrderedDict()
        tab_entry["name"] = tab.name
        if hasattr(tab, "_ui_title") and tab._ui_title and tab._ui_title != tab.name:
            tab_entry["title"] = tab._ui_title
        if getattr(tab, "highlight_type", None):
            tab_entry[exts.MDATA_HIGHLIGHT_KEY] = tab.highlight_type

        panels_data = []
        # Use iter() to get layout-ordered panels (respects bundle.yaml layout key)
        for panel in iter(tab):
            panel_name = panel.name
            panel_entry = OrderedDict()
            panel_entry["name"] = panel_name

            panel_title = getattr(panel, "_ui_title", None)
            has_custom_title = panel_title and panel_title != panel_name
            panel_meta = _collect_panel_meta(panel)

            # Build layout list for this panel
            layout_list = _build_panel_layout(panel)

            if split_panels and layout_list:
                # Write each panel to a separate .panel.yaml file.
                # Qualify by tab so same-named panels in different tabs
                # don't overwrite each other.
                panel_filename = _unique_panel_filename(
                    tab.name, panel_name, used_panel_filenames
                )
                panel_filepath = op.join(output_dir, panel_filename)
                panel_data = OrderedDict()
                if has_custom_title:
                    panel_data["title"] = panel_title
                panel_data.update(panel_meta)
                panel_data["layout"] = layout_list
                pyyaml.dump_dict(panel_data, panel_filepath)
                panel_entry["layout_file"] = panel_filename
                generated_files.append(panel_filepath)
            else:
                # Inline all layouts into extension_layout.yaml
                if has_custom_title:
                    panel_entry["title"] = panel_title
                panel_entry.update(panel_meta)
                if layout_list:
                    panel_entry["layout"] = layout_list

            panels_data.append(panel_entry)

        if panels_data:
            tab_entry["panels"] = panels_data
        tabs_data.append(tab_entry)

    # Write extension_layout.yaml
    layout_filepath = op.join(output_dir, exts.EXT_LAYOUT_FILE)
    pyyaml.dump_dict({"tabs": tabs_data}, layout_filepath)
    generated_files.insert(0, layout_filepath)

    mlogger.info(
        "Generated %d layout file(s) for %s", len(generated_files), extension_dir
    )
    return generated_files


def list_tools(extension_dir, source="auto"):
    """List all tools/commands in an extension.

    Args:
        extension_dir (str): Path to the .extension directory
        source (str): How to discover tools:
            'auto' - detect mode (layout vs legacy)
            'layout' - only scan tools/ directory
            'legacy' - only scan .tab/ directories

    Returns:
        list: Dicts with keys: name, type, path, unique_name
    """
    from pyrevit.extensions.components import Extension
    from pyrevit.extensions.parser import _parse_for_components
    from pyrevit.extensions.layout_parser import has_layout_file
    from pyrevit.extensions.toolindex import build_tool_index

    results = []

    if source == "auto":
        use_layout = has_layout_file(extension_dir)
    elif source == "layout":
        use_layout = True
    else:
        use_layout = False

    if use_layout:
        # Scan tools/ directory
        tools_dir = op.join(extension_dir, exts.TOOLS_DIR_NAME)
        if op.exists(tools_dir):
            tool_index = build_tool_index(tools_dir, extension_dir)
            for name, comp in sorted(tool_index.items()):
                results.append(
                    {
                        "name": name,
                        "type": type(comp).__name__,
                        "path": getattr(comp, "directory", ""),
                        "unique_name": getattr(comp, "unique_name", ""),
                    }
                )
    else:
        # Parse using legacy mode
        extension = Extension(cmp_path=extension_dir)
        _parse_for_components(extension)
        _collect_commands(extension, results)

    return results


def _collect_commands(component, results):
    """Recursively collect all command components.

    Args:
        component: Component to traverse
        results (list): Accumulator list
    """
    from pyrevit.extensions.genericcomps import GenericUICommand

    if isinstance(component, GenericUICommand):
        results.append(
            {
                "name": component.name,
                "type": type(component).__name__,
                "path": getattr(component, "directory", ""),
                "unique_name": getattr(component, "unique_name", ""),
            }
        )

    for child in getattr(component, "components", []):
        _collect_commands(child, results)


def _collect_background(panel):
    """Reconstruct a panel's background as a layout value (str or dict)."""
    panel_bg = getattr(panel, "panel_background", None)
    title_bg = getattr(panel, "title_background", None)
    slideout_bg = getattr(panel, "slideout_background", None)

    if title_bg or slideout_bg:
        background = OrderedDict()
        if panel_bg:
            background[exts.MDATA_BACKGROUND_PANEL_KEY] = panel_bg
        if title_bg:
            background[exts.MDATA_BACKGROUND_TITLE_KEY] = title_bg
        if slideout_bg:
            background[exts.MDATA_BACKGROUND_SLIDEOUT_KEY] = slideout_bg
        return background
    return panel_bg


def _collect_panel_meta(panel):
    """Collect a parsed panel's presentation metadata as layout keys.

    Excludes title and layout, which the caller writes separately. Only
    non-default values are emitted so generated layouts stay minimal.
    """
    meta = OrderedDict()
    if getattr(panel, "highlight_type", None):
        meta[exts.MDATA_HIGHLIGHT_KEY] = panel.highlight_type
    if getattr(panel, "collapsed", False):
        meta[exts.MDATA_COLLAPSED_KEY] = True
    if getattr(panel, "is_beta", False):
        meta[exts.MDATA_BETA_SCRIPT] = True
    background = _collect_background(panel)
    if background:
        meta[exts.MDATA_BACKGROUND_KEY] = background
    return meta


def _unique_panel_filename(tab_name, panel_name, used):
    """Build a collision-free .panel.yaml filename for a panel.

    Qualifies the filename with the tab name so two panels with the same
    name in different tabs don't share a file, and appends a numeric suffix
    if a collision still occurs.

    Args:
        tab_name (str): Name of the owning tab
        panel_name (str): Name of the panel
        used (set): Filenames already emitted in this run (mutated)

    Returns:
        str: A filename not present in ``used``.
    """
    base = "{}_{}".format(tab_name.replace(" ", ""), panel_name.replace(" ", ""))
    candidate = base + exts.PANEL_LAYOUT_POSTFIX
    idx = 2
    while candidate in used:
        candidate = "{}_{}{}".format(base, idx, exts.PANEL_LAYOUT_POSTFIX)
        idx += 1
    used.add(candidate)
    return candidate


def _build_panel_layout(panel):
    """Build a layout list from a parsed panel's components.

    Args:
        panel: Panel component with children

    Returns:
        list: Layout entries (strings and dicts)
    """
    layout = []

    # Use iter() to respect layout ordering from bundle.yaml
    for comp in iter(panel):
        type_id = getattr(comp, "type_id", "")

        if type_id == exts.SEPARATOR_IDENTIFIER:
            layout.append(layout_parser.encode_separator_entry())
        elif type_id == exts.SLIDEOUT_IDENTIFIER:
            layout.append(layout_parser.encode_slideout_entry())
        elif _is_stack_type(comp):
            # Stacks have no UI of their own; inline their children
            stack_children = [
                layout_parser.encode_tool_entry(c.name)
                for c in iter(comp)
                if getattr(c, "type_id", "")
                not in (exts.SEPARATOR_IDENTIFIER, exts.SLIDEOUT_IDENTIFIER)
            ]
            if stack_children:
                layout.append(layout_parser.encode_stack_entry(stack_children))
        else:
            layout.append(layout_parser.encode_tool_entry(comp.name))

    return layout


def _is_stack_type(comp):
    """Check if component is a stack container.

    Args:
        comp: Component to check

    Returns:
        bool: True if component is a stack type
    """
    return getattr(comp, "type_id", "") == exts.STACK_BUTTON_POSTFIX
