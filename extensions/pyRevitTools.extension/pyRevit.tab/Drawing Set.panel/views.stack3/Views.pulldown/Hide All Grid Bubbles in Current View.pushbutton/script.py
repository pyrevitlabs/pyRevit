"""Hides all grid bubbles in the active view."""

from rpw import doc, uidoc, db, DB


__min_revit_ver__ = 2016


grids = DB.FilteredElementCollector(doc)\
          .OfCategory(DB.BuiltInCategory.OST_Grids)\
          .WhereElementIsNotElementType().ToElements()

try:
    with db.Transaction('Hide Grid Bubbles'):
        for grid in grids:
            grid.HideBubbleInView(DB.DatumEnds.End0, uidoc.ActiveView)
            grid.HideBubbleInView(DB.DatumEnds.End1, uidoc.ActiveView)
except Exception:
    pass

uidoc.RefreshActiveView()
