"""Test the layout-based extension parsing system."""
#pylint: disable=E0401
import os
import os.path as op

from pyrevit import script
from pyrevit.extensions.toolindex import build_tool_index
from pyrevit.extensions.layout_parser import get_layout_file, parse_extension_layout
from pyrevit.extensions.components import Extension, Tab, Panel, GenericStack

output = script.get_output()
output.print_md("# Layout Parsing Test")

# Find extensions root
repo_root = op.dirname(op.dirname(op.dirname(op.dirname(op.dirname(
    op.dirname(op.abspath(__file__)))))))
extensions_dir = op.join(repo_root, 'extensions')

# Find all extensions with layout files
output.print_md("## Scanning for layout-enabled extensions")
layout_extensions = []
for entry in os.listdir(extensions_dir):
    ext_path = op.join(extensions_dir, entry)
    if entry.endswith('.extension') and op.isdir(ext_path):
        lf = get_layout_file(ext_path)
        if lf:
            layout_extensions.append((entry, ext_path, lf))
            output.print_md("- **{}** has layout file".format(entry))
        else:
            output.print_md("- {} (legacy mode)".format(entry))

if not layout_extensions:
    output.print_md("No extensions with layout files found!")
    script.exit()

# Test each layout-enabled extension
for ext_name, test_ext_dir, layout_file in layout_extensions:
    output.print_md("---")
    output.print_md("# Testing: {}".format(ext_name))

    output.print_md("**Extension dir:** `{}`".format(test_ext_dir))

    # Tool index building
    output.print_md("## Tool Index")
    tools_dir = op.join(test_ext_dir, 'tools')
    tool_index = build_tool_index(tools_dir, test_ext_dir)
    output.print_md("Found **{}** tools:".format(len(tool_index)))

    for name, comp in sorted(tool_index.items()):
        children = ""
        if comp.is_container:
            child_names = [c.name for c in comp.components]
            children = " children={}".format(child_names)
        output.print_md("- `{}` ({}) unique=`{}`{}".format(
            name, type(comp).__name__, comp.unique_name, children))

    if not tool_index:
        output.print_md("WARNING: No tools found in tools/ directory")

    # Full extension parsing
    output.print_md("## Extension Layout Parsing")
    extension = Extension(cmp_path=test_ext_dir)
    extension.components = []
    parse_extension_layout(extension, tool_index, layout_file)

    def print_tree(comp, indent=0):
        prefix = "&nbsp;" * (indent * 4)
        type_name = type(comp).__name__
        name = getattr(comp, 'name', '?')
        type_id = getattr(comp, 'type_id', '?')
        output.print_md("{}[**{}**] `{}` type_id=`{}`".format(
            prefix, type_name, name, type_id))
        if hasattr(comp, 'components'):
            for child in comp.components:
                print_tree(child, indent + 1)

    print_tree(extension)

    if not extension.components:
        output.print_md("**FAIL** - No components built")
    else:
        output.print_md("**PASS** - {} tab(s) built".format(
            len(extension.components)))

    # Check get_all_commands
    all_cmds = extension.get_all_commands()
    output.print_md("## Commands Found: {}".format(len(all_cmds)))
    for cmd in all_cmds:
        output.print_md("- `{}` script=`{}` class=`{}`".format(
            cmd.name,
            getattr(cmd, 'script_file', None),
            getattr(cmd, 'class_name', None)))

output.print_md("---")
output.print_md("*Test complete.*")
