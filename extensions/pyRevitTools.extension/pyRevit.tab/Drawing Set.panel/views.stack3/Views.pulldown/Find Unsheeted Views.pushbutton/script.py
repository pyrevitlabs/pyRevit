"""Lists views that have not been placed on any sheets."""

from scriptutils import this_script
from revitutils import doc, uidoc
from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory, View

views = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Views).WhereElementIsNotElementType().ToElements()

mviews = []
dviews = []

for v in views:
    if 'drafting' in str(v.ViewType).lower() and not v.IsTemplate:
        dviews.append(v)
    elif not v.IsTemplate:
        mviews.append(v)

print('DRAFTING VIEWS NOT ON ANY SHEETS'.ljust(100, '-'))
for v in dviews:
    phasep = v.LookupParameter('Phase')
    sheetnum = v.LookupParameter('Sheet Number')
    detnum = v.LookupParameter('Detail Number')
    refsheet = v.LookupParameter('Referencing Sheet')
    refviewport = v.LookupParameter('Referencing Detail')
    if sheetnum and detnum and ('-' not in sheetnum.AsString()) and ('-' not in detnum.AsString()):
        continue
    else:
        print('TYPE: {1}  ID: {2}   {0}'.format(
            v.ViewName,
            str(v.ViewType).ljust(20),
            this_script.output.linkify(v.Id),
            str(v.IsTemplate).ljust(10),
        ))

print('\n\n\n' + 'MODEL VIEWS NOT ON ANY SHEETS'.ljust(100, '-'))
for v in mviews:
    phasep = v.LookupParameter('Phase')
    sheetnum = v.LookupParameter('Sheet Number')
    detnum = v.LookupParameter('Detail Number')
    if sheetnum and detnum and ('-' not in sheetnum.AsString()) and ('-' not in detnum.AsString()):
        continue
    else:
        print('TYPE: {1}  ID: {2}   {0}'.format(
            v.ViewName,
            str(v.ViewType).ljust(20),
            this_script.output.linkify(v.Id),
            str(v.IsTemplate).ljust(10),
        ))
