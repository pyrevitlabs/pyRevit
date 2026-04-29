# -*- coding: utf-8 -*-
"""
IFC Export Demo
---------------
Demonstrates ifc_export.py from the pyRevit developer tab.
Run from within an open Revit document.
"""

import os
from pyrevit import forms, script, revit, EXEC_PARAMS
from pyrevit.interop.ifc import IFCExporter

output = script.get_output()
doc = revit.doc

# ---------------------------------------------------------------------------
# Pick an output folder
# ---------------------------------------------------------------------------
folder = forms.pick_folder(title="Select IFC output folder")
if not folder:
    script.exit()

filename = "{}.ifc".format(doc.Title)

# ---------------------------------------------------------------------------
# Optionally load a config file - skip to use defaults
# ---------------------------------------------------------------------------
use_config = forms.alert(
    "Load a Revit IFC configuration JSON file?\n\n"
    "Click Yes to browse, No to use built-in defaults.",
    yes=True,
    no=True,
)

config_path = None
if use_config:
    config_path = forms.pick_file(
        file_ext="json",
        init_dir=EXEC_PARAMS.command_path,
        title="Select IFC Configuration JSON",
    )

# ---------------------------------------------------------------------------
# Runtime overrides - edit these to test specific options
# ---------------------------------------------------------------------------
overrides = {
    "SplitWallsAndColumns": False,
    "ExportIFCCommonPropertySets": True,
    "ExportBaseQuantities": False,
    "TessellationLevelOfDetail": 0.5,  # comma bug handled automatically
    "VisibleElementsOfCurrentView": False,
    "SitePlacement": 0,  # 0=SharedCoordinates
}

# ---------------------------------------------------------------------------
# Preview what options will be applied
# ---------------------------------------------------------------------------
output.print_md("## IFC Export Demo")
output.print_md("**Document:** `{}`".format(doc.Title))
output.print_md("**Output:** `{}`".format(os.path.join(folder, filename)))
if config_path:
    output.print_md("**Config:** `{}`".format(config_path))
else:
    output.print_md("**Config:** defaults only")

output.print_md("**Runtime overrides:**")
for k, v in sorted(overrides.items()):
    output.print_md("- `{}` = `{}`".format(k, v))

# ---------------------------------------------------------------------------
# Run the export
# ---------------------------------------------------------------------------
exporter = IFCExporter(doc)

try:
    # IFC Exports have to happen in a Transaction. To avoid changes it can also be rolled back afterwards.
    with revit.Transaction("IFC Export"):
        success = exporter.export(
            folder=folder,
            filename=filename,
            config_path=config_path,
            overrides=overrides,
        )
    if success:
        output.print_md("---\n**Export complete.**")
        forms.alert(
            "IFC exported successfully.\n\n{}".format(os.path.join(folder, filename)),
            title="Done",
        )
    else:
        output.print_md("---\n**Export returned False — check Revit journal.**")
        forms.alert(
            "Export returned False.\nCheck the Revit journal file for details.",
            title="Export failed",
            warn_icon=True,
        )

except Exception as ex:
    output.print_md("---\n**Error:** `{}`".format(str(ex)))
    forms.alert("Export error:\n\n{}".format(str(ex)), title="Error", warn_icon=True)
    raise
