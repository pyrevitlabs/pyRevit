# pylint: disable=E0401
import os
import os.path as op

from pyrevit import script, forms
from pyrevit.extensions.layout_cli import generate_layout
from pyrevit.extensions.layout_parser import has_layout_file
from pyrevit.userconfig import user_config
import pyrevit.extensions as exts

split_panels = __shiftclick__  # pylint: disable=E0602

output = script.get_output()
output.print_md("# Generate Extension Layout")
if split_panels:
    output.print_md("*Mode: separate panel files*")

# Enumerate UI extensions across all configured pyRevit extension roots.
ext_dirs = []
seen = set()
for root_dir in user_config.get_ext_root_dirs():
    if not op.isdir(root_dir):
        continue
    for entry in os.listdir(root_dir):
        ext_path = op.join(root_dir, entry)
        if entry.endswith(exts.UI_EXTENSION_POSTFIX) and op.isdir(ext_path):
            key = op.normcase(op.abspath(ext_path))
            if key in seen:
                continue
            seen.add(key)
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

# Warn if extension already has a layout file
if has_layout_file(selected_dir):
    proceed = forms.alert(
        "This extension already has an extension_layout.yaml file. "
        "The generator parses legacy .tab/.panel/ folders which may "
        "no longer exist.\n\n"
        "Proceed anyway?",
        yes=True,
        no=True,
    )
    if not proceed:
        script.exit()

output.print_md("## Generating layout for: {}".format(selected))

# Ask for output directory
output_dir = forms.pick_folder(title="Select output directory (cancel for in-place)")
if not output_dir:
    output_dir = selected_dir

output.print_md("**Output directory:** `{}`".format(output_dir))

# Generate
try:
    generated = generate_layout(selected_dir, output_dir, split_panels=split_panels)
    if generated:
        output.print_md("## Generated Files")
        for f in generated:
            output.print_md("- `{}`".format(f))
        output.print_md("---")
        output.print_md("**Success!** {} file(s) generated.".format(len(generated)))

        # Show content of main layout file
        layout_file = generated[0]
        output.print_md("## extension_layout.yaml content:")
        with open(layout_file, "r") as fh:
            output.print_md("```yaml\n{}\n```".format(fh.read()))
    else:
        output.print_md("**No files generated.** Extension may have no components.")
except Exception as err:
    output.print_md("**ERROR:** {}".format(str(err)))
    import traceback

    output.print_md("```\n{}\n```".format(traceback.format_exc()))
