"""Hides all grid bubbles in the active view."""

from pyrevit import revit, DB


__min_revit_ver__ = 2016


grids = DB.FilteredElementCollector(revit.doc)\
          .OfCategory(DB.BuiltInCategory.OST_Grids)\
          .WhereElementIsNotElementType().ToElements()

try:
    with revit.Transaction('Hide Grid Bubbles'):
        for grid in grids:
            grid.HideBubbleInView(DB.DatumEnds.End0, revit.activeview)
            grid.HideBubbleInView(DB.DatumEnds.End1, revit.activeview)
except Exception:
    pass

revit.uidoc.RefreshActiveView()
