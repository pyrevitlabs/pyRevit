"""Selects all vertical reveals in the project."""

from pyrevit.framework import List
from pyrevit import revit, DB


cl = DB.FilteredElementCollector(revit.doc)
revealslist = cl.OfCategory(DB.BuiltInCategory.OST_Reveals)\
                .WhereElementIsNotElementType()\
                .ToElements()

selSet = []

for el in revealslist:
    if el.GetWallSweepInfo().IsVertical:
        selSet.append(el.Id)

revit.uidoc.Selection.SetElementIds(List[DB.ElementId](selSet))
