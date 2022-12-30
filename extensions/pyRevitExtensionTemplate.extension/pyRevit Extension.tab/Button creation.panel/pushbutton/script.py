# -*- coding: utf-8 -*-

from pyrevit import revit, forms, script
from pyrevit import DB as DB

output = script.get_output()
output.close_others()

doc = revit.doc
uidoc = revit.uidoc

wall_instances = (
    DB.FilteredElementCollector(doc)
    .OfCategory(DB.BuiltInCategory.OST_Walls)
    .WhereElementIsNotElementType()
    .ToElements()
)

output.print_md('# Hello World')
output.print_md('{0} walls found in the model.'.format(len(wall_instances)))
