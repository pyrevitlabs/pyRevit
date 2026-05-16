"""Tool index builder for layout-based extension discovery.

Scans the tools/ directory recursively, creates component objects for
each recognized bundle, and returns a name-keyed dictionary for lookup
by the layout parser.
"""
import os
import os.path as op

from pyrevit import coreutils
from pyrevit.coreutils.logger import get_logger
import pyrevit.extensions as exts
from pyrevit.extensions.parser import (
    _parse_for_components,
    _create_subcomponents,
    _get_subcomponents_classes,
)


#pylint: disable=W0703,C0302,C0103
mlogger = get_logger(__name__)


def make_layout_unique_name(extension_name, tool_name):
    """Generate unique name for layout-mode tools.

    Format: extensionname_toolname (all lowercase, cleaned).

    Args:
        extension_name (str): Name of the extension (without .extension suffix)
        tool_name (str): Name of the tool (folder name without postfix)

    Returns:
        str: Cleaned unique name
    """
    raw = exts.UNIQUE_ID_SEPARATOR.join([extension_name, tool_name])
    return coreutils.cleanup_string(
        raw, skip=[exts.UNIQUE_ID_SEPARATOR]
    ).lower()


def _get_extension_name(extension_dir):
    """Extract extension name from extension directory path.

    Args:
        extension_dir (str): Path to the .extension directory

    Returns:
        str: Extension name without .extension suffix
    """
    return op.splitext(op.basename(extension_dir))[0]


def _is_recognized_bundle(dir_path, cmp_types_list):
    """Check if a directory matches any recognized component type.

    Args:
        dir_path (str): Path to check
        cmp_types_list (list): List of component type classes

    Returns:
        type or None: The matching component type class, or None
    """
    for cmp_type in cmp_types_list:
        if cmp_type.matches(dir_path):
            return cmp_type
    return None


def build_tool_index(tools_dir, extension_dir):
    """Scan tools/ directory and legacy folder structure for tool bundles.

    Recursively walks the tools/ directory first, then scans the legacy
    .tab/.panel/ hierarchy for additional tool bundles. This allows layout
    YAML files to reference tools regardless of where they physically reside.
    Duplicates: tools/ wins (indexed first).

    Args:
        tools_dir (str): Path to the tools/ directory
        extension_dir (str): Path to the extension root

    Returns:
        dict: Mapping of tool name (str) to component object
    """
    ext_name = _get_extension_name(extension_dir)
    tool_index = {}

    # Get all known component types that can appear as tools
    # (everything that can be a child of a Panel)
    from pyrevit.extensions.components import (
        GenericStack,
        GenericUICommandGroup,
        NoScriptButton,
    )
    from pyrevit.extensions.genericcomps import (
        GenericUICommand,
    )
    panel_child_types = [GenericStack, GenericUICommandGroup,
                         GenericUICommand, NoScriptButton]
    all_cmp_types = _get_subcomponents_classes(panel_child_types)

    # Scan tools/ directory first (takes priority on duplicates)
    if op.isdir(tools_dir):
        _scan_directory(tools_dir, ext_name, tool_index, all_cmp_types)
        mlogger.debug('Built tool index with %d entries from: %s',
                      len(tool_index), tools_dir)

    # Also scan legacy folder structure (.tab/.panel/) for tool bundles
    _scan_legacy_directory(extension_dir, tools_dir, ext_name,
                           tool_index, all_cmp_types)

    mlogger.debug('Tool index has %d total entries after legacy scan',
                  len(tool_index))
    return tool_index


def _scan_directory(search_dir, ext_name, tool_index, cmp_types):
    """Recursively scan a directory for tool bundles.

    Args:
        search_dir (str): Directory to scan
        ext_name (str): Extension name for unique name generation
        tool_index (dict): Accumulator dict to populate
        cmp_types (list): List of recognized component type classes
    """
    try:
        entries = os.listdir(search_dir)
    except OSError as err:
        mlogger.error('Cannot list directory %s: %s', search_dir, err)
        return

    for entry in entries:
        # skip hidden/private entries
        if entry.startswith(('.', '_')):
            continue

        full_path = op.join(search_dir, entry)

        # only process directories
        if not op.isdir(full_path):
            continue

        matched_type = _is_recognized_bundle(full_path, cmp_types)

        if matched_type:
            # This is a recognized tool bundle
            _index_tool(full_path, matched_type, ext_name, tool_index)
        else:
            # Plain subfolder - recurse into it for organizational grouping
            _scan_directory(full_path, ext_name, tool_index, cmp_types)


def _scan_legacy_directory(extension_dir, tools_dir, ext_name,
                           tool_index, cmp_types):
    """Scan legacy .tab/.panel/ folder structure for tool bundles.

    Walks the extension directory recursively. Directories with .tab or
    .panel postfixes are treated as structural containers and recursed into.
    Tool bundles (.pushbutton, .pulldown, etc.) are indexed. Plain directories
    without recognized postfixes are skipped. The tools/ directory is skipped
    to avoid double-indexing.

    Args:
        extension_dir (str): Extension root directory to scan
        tools_dir (str): Path to tools/ directory (skipped)
        ext_name (str): Extension name for unique name generation
        tool_index (dict): Accumulator dict to populate
        cmp_types (list): List of recognized component type classes
    """
    _scan_legacy_subdir(extension_dir, tools_dir, ext_name,
                        tool_index, cmp_types)


def _scan_legacy_subdir(search_dir, tools_dir, ext_name,
                        tool_index, cmp_types):
    """Recursively scan a legacy directory for tool bundles.

    Args:
        search_dir (str): Directory to scan
        tools_dir (str): Path to tools/ directory (skipped)
        ext_name (str): Extension name for unique name generation
        tool_index (dict): Accumulator dict to populate
        cmp_types (list): List of recognized component type classes
    """
    try:
        entries = os.listdir(search_dir)
    except OSError as err:
        mlogger.error('Cannot list directory %s: %s', search_dir, err)
        return

    for entry in entries:
        # skip hidden/private entries
        if entry.startswith(('.', '_')):
            continue

        full_path = op.join(search_dir, entry)

        # only process directories
        if not op.isdir(full_path):
            continue

        # Skip the tools/ directory (already indexed)
        if tools_dir and op.normcase(op.abspath(full_path)) == \
                op.normcase(op.abspath(tools_dir)):
            continue

        # Check if this is a .tab, .panel, or .stack (structural container)
        dir_ext = _get_dir_extension(full_path)
        if dir_ext in ('.tab', '.panel', '.stack'):
            # Recurse into structural containers
            _scan_legacy_subdir(full_path, None, ext_name,
                                tool_index, cmp_types)
            continue

        # Check if this is a recognized tool bundle
        matched_type = _is_recognized_bundle(full_path, cmp_types)
        if matched_type:
            # Index tool (IndexTool skips duplicates)
            _index_tool(full_path, matched_type, ext_name, tool_index)
        # Plain directories without recognized postfix are skipped


def _get_dir_extension(dir_path):
    """Get the extension/postfix of a directory name.

    Args:
        dir_path (str): Path to the directory

    Returns:
        str: Lowercase extension (e.g. '.tab', '.panel', '.pushbutton')
    """
    name = op.basename(dir_path)
    dot_idx = name.rfind('.')
    if dot_idx > 0:
        return name[dot_idx:].lower()
    return ''


def _index_tool(tool_path, cmp_type, ext_name, tool_index):
    """Create a component from a tool directory and add to index.

    For container tools (pulldown, splitbutton), also parses their
    children recursively.

    Args:
        tool_path (str): Path to the tool bundle directory
        cmp_type (type): The component type class to instantiate
        ext_name (str): Extension name for unique name generation
        tool_index (dict): Accumulator dict to populate
    """
    try:
        component = cmp_type(cmp_path=tool_path)
    except Exception as err:
        mlogger.error('Failed to create component from %s: %s',
                      tool_path, err)
        return

    tool_name = component.name

    # Check for duplicate names
    if tool_name in tool_index:
        mlogger.warning(
            'Duplicate tool name "%s" found at %s. '
            'Skipping (first occurrence at %s wins).',
            tool_name, tool_path, tool_index[tool_name].directory
        )
        return

    # Override unique_name with layout-mode format
    component.unique_name = make_layout_unique_name(ext_name, tool_name)

    # For container tools, parse their children
    if component.is_container:
        _parse_for_components(component)
        # Update unique names for children too
        _update_child_unique_names(component, ext_name)

    tool_index[tool_name] = component
    mlogger.debug('Indexed tool: %s (%s) from %s',
                  tool_name, cmp_type.type_id, tool_path)


def _update_child_unique_names(container, ext_name):
    """Recursively update unique names for children of a container tool.

    Children of containers (e.g. buttons inside a pulldown) get unique names
    in the format: extensionname_parentname_childname.

    Args:
        container: The container component
        ext_name (str): Extension name
    """
    for child in container.components:
        child.unique_name = make_layout_unique_name(
            ext_name,
            container.name + exts.UNIQUE_ID_SEPARATOR + child.name
        )
        if child.is_container:
            _update_child_unique_names(child, ext_name)
