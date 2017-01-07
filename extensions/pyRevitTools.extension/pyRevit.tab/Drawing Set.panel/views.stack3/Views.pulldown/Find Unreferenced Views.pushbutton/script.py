"""
Copyright (c) 2014-2017 Ehsan Iran-Nejad
Python scripts for Autodesk Revit

This file is part of pyRevit repository at https://github.com/eirannejad/pyRevit

pyRevit is a free set of scripts for Autodesk Revit: you can redistribute it and/or modify
it under the terms of the GNU General Public License version 3, as published by
the Free Software Foundation.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

See this link for a copy of the GNU General Public License protecting this package.
https://github.com/eirannejad/pyRevit/blob/master/LICENSE
"""

__doc__ = 'Lists views that have not been references by any other view.'

__window__.Width = 1200
from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory, View

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
# selection = [ doc.GetElement( elId ) for elId in __revit__.ActiveUIDocument.Selection.GetElementIds() ]

views = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Views).WhereElementIsNotElementType().ToElements()

mviews = []
dviews = []

for v in views:
    if 'drafting' in str(v.ViewType).lower() and not v.IsTemplate:
        dviews.append(v)
    elif not v.IsTemplate:
        mviews.append(v)

print('UNREFERENCED DRAFTING VIEWS'.ljust(100, '-'))
for v in dviews:
    phasep = v.LookupParameter('Phase')
    sheetnum = v.LookupParameter('Sheet Number')
    detnum = v.LookupParameter('Detail Number')
    refsheet = v.LookupParameter('Referencing Sheet')
    refviewport = v.LookupParameter('Referencing Detail')
    if refsheet and refviewport and refsheet.AsString() != '' and refviewport.AsString() != '':
        continue
    else:
        print('TYPE: {1}ID: {2}TEMPLATE: {3}PHASE:{4}  {0}\nPLACED ON DETAIL/SHEET: {6} / {5}\n'.format(
            v.ViewName,
            str(v.ViewType).ljust(20),
            str(v.Id).ljust(10),
            str(v.IsTemplate).ljust(10),
            phasep.AsValueString().ljust(25) if phasep else '---'.ljust(25),
            sheetnum.AsString() if sheetnum else '-',
            detnum.AsString() if detnum else '-',
        ))

print('\n\n\n' + 'UNREFERENCED MODEL VIEWS'.ljust(100, '-'))
for v in mviews:
    phasep = v.LookupParameter('Phase')
    sheetnum = v.LookupParameter('Sheet Number')
    detnum = v.LookupParameter('Detail Number')
    refsheet = v.LookupParameter('Referencing Sheet')
    refviewport = v.LookupParameter('Referencing Detail')
    if refsheet and refviewport and refsheet.AsString() != '' and refviewport.AsString() != '':
        continue
    else:
        print('TYPE: {1}ID: {2}TEMPLATE: {3}PHASE:{4}  {0}\nPLACED ON DETAIL/SHEET: {6} / {5}\n'.format(
            v.ViewName,
            str(v.ViewType).ljust(20),
            str(v.Id).ljust(10),
            str(v.IsTemplate).ljust(10),
            phasep.AsValueString().ljust(25) if phasep else '---'.ljust(25),
            sheetnum.AsString() if sheetnum else '-',
            detnum.AsString() if detnum else '-',
        ))
