"""Get a total count and types of In Place Family in the current document.

Copyright (c) 2019 Jean-Marc Couffin
https://github.com/jmcouffin
"""
#pylint: disable=import-error,invalid-name,broad-except,superfluous-parens
from pyrevit import revit, DB
from pyrevit import script


output = script.get_output()


familyinstance_collector = DB.FilteredElementCollector(revit.doc)\
                             .OfClass(DB.FamilyInstance)\
                             .WhereElementIsNotElementType()\
                             .ToElements()

inplace_families = [
    x for x in familyinstance_collector
    if x.Symbol and x.Symbol.Family and x.Symbol.Family.IsInPlace
    ]

print('Found {} in-place families'.format(len(inplace_families)))

print('\nCATEGORY & FAMILY NAME')
report = []
for inplace_family in inplace_families:
    inplace_family_type = revit.doc.GetElement(inplace_family.GetTypeId())
    if inplace_family_type:
        category_name = inplace_family_type.Category.Name
        family_name = inplace_family.Symbol.Family.Name
        print(
            '{} category:\"{}\"  name:\"{}\"'.format(
                output.linkify(inplace_family.Id),
                category_name,
                family_name
            ))
