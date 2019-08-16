"""Selects all vertical(default) or horizontal reveals in the project.

Shift-Click:
Select horizontal reveals.
"""
#pylint: disable=import-error,invalid-name
from pyrevit import revit, DB


__title__ = "Select Vertical/Horizontal Reveals"


reveal_ids = []

for el in DB.FilteredElementCollector(revit.doc)\
            .OfCategory(DB.BuiltInCategory.OST_Reveals)\
            .WhereElementIsNotElementType()\
            .ToElements():
    if el.GetWallSweepInfo().IsVertical != __shiftclick__:      #pylint: disable=undefined-variable
        reveal_ids.append(el.Id)

revit.get_selection().set_to(reveal_ids)
