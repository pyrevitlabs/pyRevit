from pyrevit.framework import List
from pyrevit import revit, DB


textnotes = DB.FilteredElementCollector(revit.doc)\
              .OfClass(DB.TextNote)\
              .WhereElementIsNotElementType()\
              .ToElements()

selSet = []

for el in textnotes:
    selSet.append(el.Id)


revit.get_selection().set_to(selSet)
