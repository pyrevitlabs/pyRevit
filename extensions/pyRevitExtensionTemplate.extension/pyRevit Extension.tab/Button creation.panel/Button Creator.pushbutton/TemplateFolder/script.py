# -*- coding: utf-8 -*-

from pyrevit import revit, DB, forms, script

output = script.get_output()
output.close_others()

doc = revit.doc
uidoc = revit.uidoc

collector_name = (
    DB.FilteredElementCollector(doc)
    .OfCategory(DB.BuiltInCategory.OST_Walls)
    .WhereElementIsNotElementType()
    .ToElements()
)

print('Hello World')

for element in collector_name:
    print(element.Id)
