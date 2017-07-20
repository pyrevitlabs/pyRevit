"""Hides all grid bubbles in the active view."""


from rpw import doc, uidoc, db, DB

from Autodesk.Revit.DB import DatumEnds


grids = DB.FilteredElementCollector(doc)\
          .OfCategory(DB.BuiltInCategory.OST_Grids)\
          .WhereElementIsNotElementType().ToElements()


with db.Transaction('Hide Grid Bubbles'):
    for grid in grids:
        grid.HideBubbleInView(DB.DatumEnds.End0, uidoc.ActiveView)
        grid.HideBubbleInView(DB.DatumEnds.End1, uidoc.ActiveView)

uidoc.RefreshActiveView()
