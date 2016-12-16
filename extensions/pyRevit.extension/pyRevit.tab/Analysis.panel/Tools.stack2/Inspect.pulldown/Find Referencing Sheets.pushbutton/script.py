"""
Copyright (c) 2014-2016 Ehsan Iran-Nejad
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

__doc__ = 'Find all sheets referencing the current view. Especially useful for finding legends.'

from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory, ScheduleSheetInstance

doc = __revit__.ActiveUIDocument.Document

cl_views = FilteredElementCollector(doc)
shts = cl_views.OfCategory(BuiltInCategory.OST_Sheets).WhereElementIsNotElementType().ToElements()
sheets = sorted(shts, key=lambda x: x.SheetNumber)

curview = doc.ActiveView
count = 0

print('Searching All Sheets for {0} ID:{1}\n'.format(curview.Name, curview.Id))
for s in sheets:
    vpsIds = [doc.GetElement(x).ViewId for x in s.GetAllViewports()]
    curviewelements = FilteredElementCollector(doc).OwnedByView(s.Id).WhereElementIsNotElementType().ToElements()
    for el in curviewelements:
        if isinstance(el, ScheduleSheetInstance):
            vpsIds.append(el.ScheduleId)
    if curview.Id in vpsIds:
        count += 1
        print('NUMBER: {0}   NAME:{1}'.format(s.LookupParameter('Sheet Number').AsString().rjust(10),
                                              s.LookupParameter('Sheet Name').AsString().ljust(50)
                                              ))

print('\n\nView is referenced on {0} sheets.'.format(count))
