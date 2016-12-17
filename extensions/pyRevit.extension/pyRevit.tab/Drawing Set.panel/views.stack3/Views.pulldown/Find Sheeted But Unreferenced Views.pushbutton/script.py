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

__doc__ = 'List all views that have been placed on a sheet but are not referenced by any other views.'

__window__.Width = 1200

from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory, View

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

views = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Views).WhereElementIsNotElementType().ToElements()

mviews = []
dviews = []

# separating model view and drafting view from the full view list
for v in views:
    if 'drafting' in str(v.ViewType).lower() and not v.IsTemplate:
        dviews.append(v)
    elif not v.IsTemplate:
        mviews.append(v)

print('DRAFTING VIEWS NOT ON ANY SHEETS' + '-' * 80)

for v in dviews:
    sheetnum = v.LookupParameter('Sheet Number')
    detnum = v.LookupParameter('Detail Number')
    refsheet = v.LookupParameter('Referencing Sheet')
    refviewport = v.LookupParameter('Referencing Detail')
    # is the view placed on a sheet?
    if sheetnum and detnum and ('-' not in sheetnum.AsString()) and ('-' not in detnum.AsString()):
        # is the view referenced by at least one other view?
        if refsheet and refviewport and refsheet.AsString() != '' and refviewport.AsString() != '':
            continue
        else:
            # print the view sheet and det number
            print('DET/SHEET: {1}ID: {2}NAME: {0}'.format(v.ViewName,
                                                          unicode(detnum.AsString() + '/' + sheetnum.AsString()).ljust(
                                                              10),
                                                          str(v.Id).ljust(10)
                                                          ))

print('\n'
      '\n'
      '\n'
      'MODEL VIEWS NOT ON ANY SHEETS' + '-' * 80)

for v in mviews:
    sheetnum = v.LookupParameter('Sheet Number')
    detnum = v.LookupParameter('Detail Number')
    refsheet = v.LookupParameter('Referencing Sheet')
    refviewport = v.LookupParameter('Referencing Detail')
    # is the view placed on a sheet?
    if sheetnum and detnum and ('-' not in sheetnum.AsString()) and ('-' not in detnum.AsString()):
        # is the view referenced by at least one other view?
        if refsheet and refviewport and refsheet.AsString() != '' and refviewport.AsString() != '':
            continue
        else:
            # print the view sheet and det number
            print('DET/SHEET: {1}ID: {2}NAME: {0}'.format(v.ViewName,
                                                          str(detnum.AsString() + '/' + sheetnum.AsString()).ljust(10),
                                                          str(v.Id).ljust(10)
                                                          ))
