"""CLI utilities for layout-based extension management.

Provides commands to:
- Generate layout YAML from an existing legacy extension
- List all tools in an extension (layout or legacy mode)

These can be invoked as developer pushbutton scripts in Revit,
or called programmatically.
"""
import os
import os.path as op
import codecs
from collections import OrderedDict

from pyrevit.coreutils.logger import get_logger
import pyrevit.extensions as exts


#pylint: disable=W0703,C0302,C0103
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
        mlogger.warning('No components found in extension: %s', extension_dir)
        return []

    generated_files = []

    # Build the extension_layout.yaml content
    tabs_data = []
    for tab in extension.components:
        tab_entry = OrderedDict()
        tab_entry['name'] = tab.name
        if hasattr(tab, '_ui_title') and tab._ui_title and tab._ui_title != tab.name:
            tab_entry['title'] = tab._ui_title

        panels_data = []
        # Use iter() to get layout-ordered panels (respects bundle.yaml layout key)
        for panel in iter(tab):
            panel_name = panel.name
            panel_entry = OrderedDict()
            panel_entry['name'] = panel_name

            # Build layout list for this panel
            layout_list = _build_panel_layout(panel)

            if layout_list:
                if split_panels:
                    # Write each panel to a separate .panel.yaml file
                    panel_filename = panel_name.replace(' ', '') + '.panel.yaml'
                    panel_filepath = op.join(output_dir, panel_filename)
                    _write_panel_yaml(panel_filepath, panel_name, layout_list)
                    panel_entry['layout_file'] = panel_filename
                    generated_files.append(panel_filepath)
                else:
                    # Inline all layouts into extension_layout.yaml
                    panel_entry['layout'] = layout_list

            panels_data.append(panel_entry)

        if panels_data:
            tab_entry['panels'] = panels_data
        tabs_data.append(tab_entry)

    # Write extension_layout.yaml
    layout_content = _serialize_layout_yaml({'tabs': tabs_data})
    layout_filepath = op.join(output_dir, exts.EXT_LAYOUT_FILE)
    with codecs.open(layout_filepath, 'w', 'utf-8') as f:
        f.write(layout_content)
    generated_files.insert(0, layout_filepath)

    mlogger.info('Generated %d layout file(s) for %s',
                 len(generated_files), extension_dir)
    return generated_files


def list_tools(extension_dir, source='auto'):
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

    if source == 'auto':
        use_layout = has_layout_file(extension_dir)
    elif source == 'layout':
        use_layout = True
    else:
        use_layout = False

    if use_layout:
        # Scan tools/ directory
        tools_dir = op.join(extension_dir, exts.TOOLS_DIR_NAME)
        if op.exists(tools_dir):
            tool_index = build_tool_index(tools_dir, extension_dir)
            for name, comp in sorted(tool_index.items()):
                results.append({
                    'name': name,
                    'type': type(comp).__name__,
                    'path': getattr(comp, 'directory', ''),
                    'unique_name': getattr(comp, 'unique_name', ''),
                })
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
        results.append({
            'name': component.name,
            'type': type(component).__name__,
            'path': getattr(component, 'directory', ''),
            'unique_name': getattr(component, 'unique_name', ''),
        })

    for child in getattr(component, 'components', []):
        _collect_commands(child, results)


def _build_panel_layout(panel):
    """Build a layout list from a parsed panel's components.

    Args:
        panel: Panel component with children

    Returns:
        list: Layout entries (strings and dicts)
    """
    layout = []
    stack_buffer = []

    # Use iter() to respect layout ordering from bundle.yaml
    for comp in iter(panel):
        type_id = getattr(comp, 'type_id', '')

        if type_id == exts.SEPARATOR_IDENTIFIER:
            # Flush any pending stack
            if stack_buffer:
                layout.append({'stack': stack_buffer})
                stack_buffer = []
            layout.append('---')
        elif type_id == exts.SLIDEOUT_IDENTIFIER:
            if stack_buffer:
                layout.append({'stack': stack_buffer})
                stack_buffer = []
            layout.append('>>>')
        elif _is_stack_type(comp):
            # This is a stack - inline its children (iter respects bundle.yaml order)
            stack_children = [c.name for c in iter(comp)
                              if getattr(c, 'type_id', '') not in
                              (exts.SEPARATOR_IDENTIFIER, exts.SLIDEOUT_IDENTIFIER)]
            if stack_children:
                layout.append({'stack': stack_children})
        else:
            # Regular tool
            layout.append(comp.name)

    # Flush remaining stack buffer
    if stack_buffer:
        layout.append({'stack': stack_buffer})

    return layout


def _is_stack_type(comp):
    """Check if component is a stack container.

    Args:
        comp: Component to check

    Returns:
        bool: True if component is a stack type
    """
    type_id = getattr(comp, 'type_id', '')
    return type_id and 'stack' in type_id.lower()


def _serialize_layout_yaml(data):
    """Serialize layout data to YAML string.

    Produces clean, human-readable YAML without relying on YamlDotNet
    serializer (which may not handle Python dicts well in IronPython).

    Args:
        data (dict): Layout data structure

    Returns:
        str: YAML string
    """
    lines = []
    _yaml_dump(data, lines, indent=0)
    return '\n'.join(lines) + '\n'


def _yaml_dump(obj, lines, indent):
    """Recursively dump a Python object to YAML lines.

    Args:
        obj: Object to serialize (dict, list, or scalar)
        lines (list): Accumulator for output lines
        indent (int): Current indentation level
    """
    prefix = '  ' * indent

    if isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(value, (dict, list)):
                lines.append('%s%s:' % (prefix, key))
                _yaml_dump(value, lines, indent + 1)
            else:
                lines.append('%s%s: %s' % (prefix, key, _yaml_scalar(value)))
    elif isinstance(obj, list):
        for item in obj:
            if isinstance(item, dict):
                # First key on the same line as the dash
                keys = list(item.keys())
                if keys:
                    first_key = keys[0]
                    first_val = item[first_key]
                    if isinstance(first_val, (dict, list)):
                        lines.append('%s- %s:' % (prefix, first_key))
                        _yaml_dump(first_val, lines, indent + 2)
                    else:
                        lines.append('%s- %s: %s' % (prefix, first_key,
                                                      _yaml_scalar(first_val)))
                    # Remaining keys at deeper indent
                    for key in keys[1:]:
                        val = item[key]
                        if isinstance(val, (dict, list)):
                            lines.append('%s  %s:' % (prefix, key))
                            _yaml_dump(val, lines, indent + 2)
                        else:
                            lines.append('%s  %s: %s' % (prefix, key,
                                                          _yaml_scalar(val)))
            else:
                lines.append('%s- %s' % (prefix, _yaml_scalar(item)))


def _yaml_scalar(value):
    """Format a scalar value for YAML output.

    Args:
        value: Scalar value to format

    Returns:
        str: Formatted YAML scalar
    """
    if value is None:
        return 'null'
    s = str(value)
    # Quote if contains special chars or looks like a YAML directive
    if any(c in s for c in (':', '#', '{', '}', '[', ']', ',', '&', '*',
                            '?', '|', '-', '<', '>', '=', '!', '%', '@',
                            '`')):
        return '"%s"' % s.replace('"', '\\"')
    if s in ('true', 'false', 'null', 'yes', 'no', 'on', 'off'):
        return '"%s"' % s
    return '"%s"' % s


def _write_panel_yaml(filepath, panel_name, layout_list):
    """Write a panel.yaml file.

    Args:
        filepath (str): Output file path
        panel_name (str): Panel display name/title
        layout_list (list): Layout entries
    """
    data = OrderedDict()
    data['title'] = panel_name
    data['layout'] = layout_list
    content = _serialize_layout_yaml(data)
    with codecs.open(filepath, 'w', 'utf-8') as f:
        f.write(content)
