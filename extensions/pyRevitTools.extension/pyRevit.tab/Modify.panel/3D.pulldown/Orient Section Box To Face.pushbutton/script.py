"""Aligns the section box of the current 3D view to selected face."""

from pyrevit import revit, DB, forms
from sbox.sbox_actions import align_to_face


if isinstance(revit.active_view, DB.View3D) and revit.active_view.IsSectionBoxActive:
    align_to_face(revit.doc, revit.uidoc)
elif isinstance(revit.active_view, DB.View3D) and not revit.active_view.IsSectionBoxActive:
    forms.alert("The section box for View3D isn't active.")
else:
    forms.alert("You must be on a 3D view for this tool to work.")
