"""Resets element graphic override for the selected elements."""

from pyrevit import revit, DB


selection = revit.get_selection()


with revit.Transaction('Reset Element Override'):
    for el in selection:
        ogs = DB.OverrideGraphicSettings()
        revit.doc.ActiveView.SetElementOverrides(el.Id, ogs)
