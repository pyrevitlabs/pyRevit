"""Hides all grid bubbles in the active view."""


from pyrevit.revit import doc, DB


grids = DB.FilteredElementCollector(__activedoc__)\
          .OfCategory(DB.BuiltInCategory.OST_Grids)\
          .WhereElementIsNotElementType().ToElements()


with doc.Transaction('Hide Grid Bubbles'):
    activeview = __activeuidoc__.ActiveView
    for grid in grids:
        grid.HideBubbleInView(DB.DatumEnds.End0, activeview)
        grid.HideBubbleInView(DB.DatumEnds.End1, activeview)

__activeuidoc__.RefreshActiveView()
