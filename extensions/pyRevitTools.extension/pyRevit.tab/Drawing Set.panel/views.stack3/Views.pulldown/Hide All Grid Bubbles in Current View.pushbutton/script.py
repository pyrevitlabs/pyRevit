"""Hides all grid bubbles in the active view."""


from pyrevit import revit, DB


grids = DB.FilteredElementCollector(revit.doc)\
          .OfCategory(DB.BuiltInCategory.OST_Grids)\
          .WhereElementIsNotElementType().ToElements()


with revit.Transaction('Hide Grid Bubbles'):
    activeview = revit.activeview
    for grid in grids:
        grid.HideBubbleInView(DB.DatumEnds.End0, activeview)
        grid.HideBubbleInView(DB.DatumEnds.End1, activeview)

revit.uidoc.RefreshActiveView()
