"""Layout-based extension parser.

Reads extension_layout.yaml and *.panel.yaml files, resolves tool
references against a tool index, and builds the component tree that
uimaker.py consumes.
"""
import os
import os.path as op

from pyrevit import coreutils
from pyrevit.coreutils import yaml
from pyrevit.coreutils.logger import get_logger
import pyrevit.extensions as exts
from pyrevit.extensions.genericcomps import (
    GenericUIComponent,
    GenericUIContainer,
    LayoutItem,
)
from pyrevit.extensions.toolindex import make_layout_unique_name


#pylint: disable=W0703,C0302,C0103
mlogger = get_logger(__name__)


def has_layout_file(extension_dir):
    """Check if extension_layout.yaml exists in extension directory.

    Args:
        extension_dir (str): Path to the .extension directory

    Returns:
        bool: True if layout file found
    """
    return op.isfile(op.join(extension_dir, exts.EXT_LAYOUT_FILE))


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
    # Check user config for custom layout path
    try:
        from pyrevit.userconfig import user_config
        # Global toggle: skip custom layouts when disabled
        if not user_config.disable_custom_layouts:
            ext_name = op.splitext(op.basename(extension_dir))[0]
            section_name = ext_name + '.extension'
            if user_config.has_section(section_name):
                section = user_config.get_section(section_name)
                custom_path = section.get_option('custom_layout_path',
                                                 default_value='')
                if custom_path and op.isfile(custom_path):
                    return custom_path
    except Exception:
        pass

    # Bundled layout file
    bundled = op.join(extension_dir, exts.EXT_LAYOUT_FILE)
    if op.isfile(bundled):
        return bundled
    return None


def parse_extension_layout(extension, tool_index, layout_file):
    """Parse layout file and build Tab/Panel/Tool tree on extension.

    Reads the layout YAML, creates Tab and Panel containers, resolves
    tool references from the tool index, and populates the extension's
    component tree.

    Args:
        extension: Extension object to populate
        tool_index (dict): Mapping of tool name to component object
        layout_file (str): Path to the extension_layout.yaml file
    """
    ext_dir = extension.directory
    ext_name = op.splitext(op.basename(ext_dir))[0]

    try:
        layout_data = yaml.load_as_dict(layout_file)
    except Exception as err:
        mlogger.error('Failed to read layout file %s: %s', layout_file, err)
        return

    if not layout_data:
        mlogger.warning('Layout file is empty: %s', layout_file)
        return

    tabs_data = layout_data.get(exts.LAYOUT_TABS_KEY, [])
    if not tabs_data:
        mlogger.warning('No tabs defined in layout file: %s', layout_file)
        return

    layout_dir = op.dirname(layout_file)
    referenced_tools = set()

    for tab_data in tabs_data:
        tab = _create_tab(tab_data, ext_name, ext_dir)
        if tab is None:
            continue

        panels_data = tab_data.get(exts.LAYOUT_PANELS_KEY, [])
        for panel_data in panels_data:
            panel = _create_panel(panel_data, ext_name, ext_dir, tool_index,
                                  layout_dir, referenced_tools)
            if panel is not None:
                tab.add_component(panel)

        extension.add_component(tab)

    # Attach tools not referenced in the layout as assembly-only commands.
    # They get compiled into the DLL but don't appear in the ribbon,
    # so layout changes don't require a new assembly build.
    unreferenced = [comp for name, comp in tool_index.items()
                    if name not in referenced_tools]
    if unreferenced:
        extension._assembly_only_commands = unreferenced
        mlogger.debug('Layout: %d tool(s) not in layout, '
                      'included as assembly-only', len(unreferenced))

    mlogger.debug('Layout parsing complete for %s: %d tab(s)',
                  ext_name, len(extension.components))


def _create_tab(tab_data, ext_name, ext_dir):
    """Create a Tab component from layout YAML data.

    Args:
        tab_data (dict): Tab definition from YAML
        ext_name (str): Extension name
        ext_dir (str): Extension directory path

    Returns:
        Tab or None: Created tab component
    """
    from pyrevit.extensions.components import Tab

    tab_name = tab_data.get(exts.LAYOUT_NAME_KEY)
    if not tab_name:
        mlogger.error('Tab definition missing "name" key')
        return None

    tab = Tab(cmp_path=None)
    tab.name = tab_name
    tab._ui_title = tab_data.get(exts.LAYOUT_TITLE_KEY, tab_name)
    tab.unique_name = make_layout_unique_name(ext_name, tab_name)

    mlogger.debug('Created layout tab: %s', tab_name)
    return tab


def _create_panel(panel_data, ext_name, ext_dir, tool_index, layout_dir=None,
                  referenced_tools=None):
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
    from pyrevit.extensions.components import Panel

    if layout_dir is None:
        layout_dir = ext_dir

    # panel_data can be a dict with name + layout/layout_file
    if isinstance(panel_data, str):
        # Simple string reference - look for panel.yaml file
        panel_name = panel_data
        panel_title = panel_data
        layout_list = _load_panel_layout_file(panel_name, ext_dir,
                                              layout_dir)
    elif isinstance(panel_data, dict):
        panel_name = panel_data.get(exts.LAYOUT_NAME_KEY)
        if not panel_name:
            mlogger.error('Panel definition missing "name" key')
            return None
        panel_title = panel_data.get(exts.LAYOUT_TITLE_KEY, panel_name)

        # Check for external layout file reference
        layout_file_ref = panel_data.get(exts.LAYOUT_FILE_KEY)
        if layout_file_ref:
            # Try layout directory first (custom cached layouts), then ext_dir
            filepath = op.join(layout_dir, layout_file_ref)
            if not op.isfile(filepath):
                filepath = op.join(ext_dir, layout_file_ref)
            layout_list = _load_panel_layout_file_path(filepath)
        else:
            # Inline layout
            layout_list = panel_data.get(exts.LAYOUT_KEY, [])
    else:
        mlogger.error('Invalid panel definition type: %s', type(panel_data))
        return None

    panel = Panel(cmp_path=None)
    panel.name = panel_name
    panel._ui_title = panel_title
    panel.unique_name = make_layout_unique_name(ext_name, panel_name)

    if layout_list:
        _populate_panel(panel, layout_list, tool_index, ext_name,
                        referenced_tools)

    mlogger.debug('Created layout panel: %s with %d component(s)',
                  panel_name, len(panel.components))
    return panel


def _load_panel_layout_file(panel_name, ext_dir, layout_dir=None):
    """Load a panel layout from {PanelName}.panel.yaml.

    Checks layout_dir first (for custom cached layouts), then ext_dir.

    Args:
        panel_name (str): Panel name to look up
        ext_dir (str): Extension directory path
        layout_dir (str): Directory of the active layout file

    Returns:
        list: Layout entries, or empty list if not found
    """
    filename = panel_name + exts.PANEL_LAYOUT_POSTFIX
    # Try layout directory first (custom cached layouts)
    if layout_dir:
        filepath = op.join(layout_dir, filename)
        if op.isfile(filepath):
            return _load_panel_layout_file_path(filepath)
    # Fall back to extension directory
    filepath = op.join(ext_dir, filename)
    return _load_panel_layout_file_path(filepath)


def _load_panel_layout_file_path(filepath):
    """Load panel layout from a specific file path.

    Args:
        filepath (str): Path to the .panel.yaml file

    Returns:
        list: Layout entries, or empty list if not found
    """
    if not op.isfile(filepath):
        mlogger.debug('Panel layout file not found: %s', filepath)
        return []

    try:
        panel_data = yaml.load_as_dict(filepath)
    except Exception as err:
        mlogger.error('Failed to read panel layout file %s: %s',
                      filepath, err)
        return []

    if not panel_data:
        return []

    return panel_data.get(exts.LAYOUT_KEY, [])


def _populate_panel(panel, layout_list, tool_index, ext_name,
                    referenced_tools=None):
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
        if isinstance(entry, str):
            # String entry: tool name, separator, or slideout
            _resolve_string_entry(entry, panel, tool_index,
                                  referenced_tools)
        elif isinstance(entry, dict):
            # Dict entry: could be a stack grouping
            if exts.LAYOUT_STACK_KEY in entry:
                stack_children = entry[exts.LAYOUT_STACK_KEY]
                _create_stack(
                    stack_children, panel, tool_index,
                    ext_name, stack_counter, referenced_tools
                )
                stack_counter += 1
            else:
                mlogger.warning(
                    'Unknown dict entry in panel layout: %s', entry
                )
        else:
            mlogger.warning(
                'Unknown layout entry type (%s): %s',
                type(entry), entry
            )


def _resolve_string_entry(entry, parent, tool_index, referenced_tools=None):
    """Resolve a string layout entry and add to parent.

    Handles:
        - Separator identifiers ('---')
        - Slideout identifiers ('>>>' or '>>>>>')
        - Tool name references (lookup in tool_index)

    Args:
        entry (str): The string entry from layout YAML
        parent: Parent container to add component to
        tool_index (dict): Tool name to component mapping
        referenced_tools (set): Set to track tool names placed in the layout
    """
    # Check for separator
    if exts.SEPARATOR_IDENTIFIER in entry:
        separator = GenericUIComponent()
        separator.type_id = exts.SEPARATOR_IDENTIFIER
        separator.name = exts.SEPARATOR_IDENTIFIER
        parent.add_component(separator)
        return

    # Check for slideout
    if exts.SLIDEOUT_IDENTIFIER in entry:
        slideout = GenericUIComponent()
        slideout.type_id = exts.SLIDEOUT_IDENTIFIER
        slideout.name = exts.SLIDEOUT_IDENTIFIER
        parent.add_component(slideout)
        return

    # Tool name reference
    tool_name = entry.strip()
    if tool_name in tool_index:
        parent.add_component(tool_index[tool_name])
        if referenced_tools is not None:
            referenced_tools.add(tool_name)
    else:
        mlogger.warning(
            'Tool "%s" referenced in layout but not found in tool index',
            tool_name
        )


def _create_stack(children_names, panel, tool_index, ext_name, stack_idx,
                  referenced_tools=None):
    """Create a GenericStack with children from tool index.

    Args:
        children_names (list): List of tool name strings
        panel: Parent panel to add stack to
        tool_index (dict): Tool name to component mapping
        ext_name (str): Extension name
        stack_idx (int): Stack counter for unique name generation
        referenced_tools (set): Set to track tool names placed in the layout
    """
    from pyrevit.extensions.components import GenericStack

    stack_name = '_stack_%d' % stack_idx
    stack = GenericStack(cmp_path=None)
    stack.name = stack_name
    stack.unique_name = make_layout_unique_name(ext_name, stack_name)

    for child_name in children_names:
        if not isinstance(child_name, str):
            mlogger.warning(
                'Stack child must be a string tool name, got: %s',
                type(child_name)
            )
            continue

        child_name = child_name.strip()
        if child_name in tool_index:
            stack.add_component(tool_index[child_name])
            if referenced_tools is not None:
                referenced_tools.add(child_name)
        else:
            mlogger.warning(
                'Tool "%s" referenced in stack but not found in tool index',
                child_name
            )

    if stack.components:
        panel.add_component(stack)
    else:
        mlogger.warning('Stack %s has no valid children, skipping', stack_name)
