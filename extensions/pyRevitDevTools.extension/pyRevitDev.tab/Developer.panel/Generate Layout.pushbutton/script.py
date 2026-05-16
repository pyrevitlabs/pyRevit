"""Generate extension_layout.yaml from a legacy extension.

Select an extension directory and this script will parse it using the
legacy folder-walking parser, then generate YAML layout files that
reproduce the same UI structure.
"""
#pylint: disable=E0401
import os
import os.path as op

from pyrevit import script, forms
from pyrevit.extensions.layout_cli import generate_layout

__title__ = "Generate\nLayout"
__doc__ = "Generate extension_layout.yaml from a legacy extension's folder structure"

output = script.get_output()
output.print_md("# Generate Extension Layout")

# Find extensions root
repo_root = op.dirname(op.dirname(op.dirname(op.dirname(op.dirname(
    op.dirname(op.abspath(__file__)))))))
extensions_dir = op.join(repo_root, 'extensions')

# List available extensions
ext_dirs = []
for entry in os.listdir(extensions_dir):
    ext_path = op.join(extensions_dir, entry)
    if entry.endswith('.extension') and op.isdir(ext_path):
        ext_dirs.append(ext_path)

if not ext_dirs:
    output.print_md("**No extensions found!**")
    script.exit()

# Let user pick an extension
ext_names = [op.basename(d) for d in ext_dirs]
selected = forms.SelectFromList.show(
    ext_names,
    title="Select Extension",
    multiselect=False
)

if not selected:
    script.exit()

selected_dir = ext_dirs[ext_names.index(selected)]
output.print_md("## Generating layout for: {}".format(selected))

# Ask for output directory
output_dir = forms.pick_folder(title="Select output directory (cancel for in-place)")
if not output_dir:
    output_dir = selected_dir

output.print_md("**Output directory:** `{}`".format(output_dir))

# Generate
try:
    generated = generate_layout(selected_dir, output_dir)
    if generated:
        output.print_md("## Generated Files")
        for f in generated:
            output.print_md("- `{}`".format(f))
        output.print_md("---")
        output.print_md("**Success!** {} file(s) generated.".format(len(generated)))

        # Show content of main layout file
        layout_file = generated[0]
        output.print_md("## extension_layout.yaml content:")
        with open(layout_file, 'r') as fh:
            output.print_md("```yaml\n{}\n```".format(fh.read()))
    else:
        output.print_md("**No files generated.** Extension may have no components.")
except Exception as err:
    output.print_md("**ERROR:** {}".format(str(err)))
    import traceback
    output.print_md("```\n{}\n```".format(traceback.format_exc()))
