# -*- coding: utf-8 -*-
"""Developer example: pick an element, display a number on it via AVF.

Minimal end-to-end smoke test for pyrevit.revit.avf. Pick any element
visible in the active view, type in a number, and it gets painted onto the
element. Orthographic 3D views without a section box also offer a colored
surface instead of a text marker.
"""

from pyrevit import DB, revit, forms
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
if (
    isinstance(view, DB.View3D)
    and not view.IsPerspective
    and not view.IsSectionBoxActive
):
    style_choice = forms.CommandSwitchWindow.show(
        ["Text Marker", "Colored Surface"],
        message="Pick an AVF display style:",
    )
else:
    style_choice = "Text Marker"

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

elem_id_val = list(results.keys())[0]
success, sfp_id = results[elem_id_val]

if success:
    surface_hint = (
        "If the surface stays uncolored, Revit accepted no face of this "
        "element. Run again and pick Text Marker.\n\n"
        if style_choice == "Colored Surface"
        else ""
    )
    forms.alert(
        "Displayed value {} on element ID {}.\n\n"
        "{}"
        "Run again on other elements, or use "
        "avf.clear_avf_results(view) to remove all markers from "
        "this view.".format(value, elem_id_val, surface_hint)
    )
else:
    forms.alert(
        "Could not display a value on the selected element.\n"
        "Check that it is visible in the active view. The pyRevit output "
        "window shows the error."
    )
