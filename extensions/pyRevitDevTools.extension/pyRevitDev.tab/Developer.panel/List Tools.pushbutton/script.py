# pylint: disable=E0401
import os
import os.path as op

from pyrevit import script, forms
from pyrevit.extensions.layout_cli import list_tools
from pyrevit.extensions.layout_parser import has_layout_file
import pyrevit.extensions as exts

output = script.get_output()
output.print_md("# Extension Tool List")

# Find extensions root
repo_root = op.dirname(
    op.dirname(op.dirname(op.dirname(op.dirname(op.dirname(op.abspath(__file__))))))
)
extensions_dir = op.join(repo_root, "extensions")

# List available extensions
ext_dirs = []
for entry in os.listdir(extensions_dir):
    ext_path = op.join(extensions_dir, entry)
    if entry.endswith(exts.UI_EXTENSION_POSTFIX) and op.isdir(ext_path):
        ext_dirs.append(ext_path)

if not ext_dirs:
    output.print_md("**No extensions found!**")
    script.exit()

# Let user pick an extension
ext_names = [op.basename(d) for d in ext_dirs]
selected = forms.SelectFromList.show(
    ext_names, title="Select Extension", multiselect=False
)

if not selected:
    script.exit()

selected_dir = ext_dirs[ext_names.index(selected)]
mode = "layout" if has_layout_file(selected_dir) else "legacy"
output.print_md("## Extension: {} (mode: {})".format(selected, mode))

# List tools
try:
    tools = list_tools(selected_dir)
    if tools:
        output.print_md("Found **{}** tool(s):".format(len(tools)))
        output.print_md("")
        output.print_md("| Name | Type | Unique Name |")
        output.print_md("|------|------|-------------|")
        for tool in tools:
            output.print_md(
                "| {} | {} | `{}` |".format(
                    tool["name"], tool["type"], tool["unique_name"]
                )
            )
    else:
        output.print_md("**No tools found.**")
except Exception as err:
    output.print_md("**ERROR:** {}".format(str(err)))
    import traceback

    output.print_md("```\n{}\n```".format(traceback.format_exc()))
