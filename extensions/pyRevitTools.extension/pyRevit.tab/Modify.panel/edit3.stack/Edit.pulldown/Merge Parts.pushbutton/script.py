"""Merge selected parts into one element."""
#pylint: disable=import-error,invalid-name,broad-except
from pyrevit import revit, DB
from pyrevit.framework import List
from pyrevit import forms
from pyrevit import script

__author__ = "{{author}}"
__context__ = "selection"


logger = script.get_logger()
output = script.get_output()


part_ids = [x.Id for x in revit.get_selection() if isinstance(x, DB.Part)]

with revit.Transaction("Merge parts"):
    DB.PartUtils.CreateMergedPart(
        revit.doc,
        List[DB.ElementId](part_ids)
    )