"""Selects all vertical/horizontal reveals in the project.
By default selects vertical ones. With Shift-CLick: horizontal."""
__title__ = "Select vertical/horizontal Reveals"
from pyrevit.framework import List
from pyrevit import revit, DB


cl = DB.FilteredElementCollector(revit.doc)
revealslist = cl.OfCategory(DB.BuiltInCategory.OST_Reveals)\
                .WhereElementIsNotElementType()\
                .ToElements()

selSet = []

for el in revealslist:
    if el.GetWallSweepInfo().IsVertical != __shiftclick__:
        selSet.append(el.Id)

revit.get_selection().set_to(selSet)
