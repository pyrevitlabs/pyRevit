# -*- coding: utf-8 -*-
"""Developer example: pick an element, display a number on it via AVF.

Minimal end-to-end smoke test for pyrevit.revit.avf. Pick any element with
solid geometry visible in the active view, type in a number, choose a
display style (text marker or colored surface), and it gets painted onto
the element.
"""

from pyrevit import revit, forms
from pyrevit.revit import avf

doc = revit.doc
view = revit.active_view

# 1. Pick a single element in the model
with forms.WarningBar(title="Select an element to label"):
    element = revit.pick_element()

if not element:
    forms.alert("Nothing selected.", exitscript=True)

# 2. Ask for a value to display
value_str = forms.ask_for_string(
    default="42",
    prompt="Value to display on the selected element:",
    title="AVF Demo",
)

if value_str is None:
    forms.alert("Cancelled.", exitscript=True)

try:
    value = float(value_str)
except ValueError:
    forms.alert("'{}' is not a number.".format(value_str), exitscript=True)

# 3. Pick a display style, get-or-create it, and assign it to the view.
style_choice = forms.CommandSwitchWindow.show(
    ["Text Marker", "Colored Surface"],
    message="Pick an AVF display style:",
)

if style_choice is None:
    forms.alert("Cancelled.", exitscript=True)

if style_choice == "Colored Surface":
    style = avf.get_or_create_colored_surface_display_style(
        doc, "pyRevitAVF_Demo_ColoredSurface"
    )
else:
    style = avf.get_or_create_marker_display_style(doc, "pyRevitAVF_Demo_Marker")

with revit.Transaction("Set AVF Display Style"):
    view.AnalysisDisplayStyleId = style.Id

results = avf.display_avf_values(
    {element: value},
    view,
    schema_name="pyRevitAVF_Demo",
    schema_desc="AVF pick-and-display demo",
)

elem_id_val = results.keys()[0]
success, sfp_id = results[elem_id_val]

if success:
    forms.alert(
        "Displayed value {} on element ID {}.\n\n"
        "Run again on other elements, or use "
        "avf.clear_avf_results(view) to remove all markers from "
        "this view.".format(value, elem_id_val)
    )
else:
    forms.alert(
        "Could not find a viewer-facing face on the selected element.\n"
        "Try an element with solid geometry (wall, floor, generic model), "
        "or adapt the script to pass use_bbox_center=True."
    )
