"""Selects all vertical(default) or horizontal reveals in the project.

Shift-Click:
Select horizontal reveals.
"""
#pylint: disable=import-error,invalid-name
from pyrevit import revit, DB, EXEC_PARAMS


reveal_ids = []

for el in DB.FilteredElementCollector(revit.doc)\
            .OfCategory(DB.BuiltInCategory.OST_Reveals)\
            .WhereElementIsNotElementType()\
            .ToElements():
    if el.GetWallSweepInfo().IsVertical != EXEC_PARAMS.config_mode:
        reveal_ids.append(el.Id)

revit.get_selection().set_to(reveal_ids)
