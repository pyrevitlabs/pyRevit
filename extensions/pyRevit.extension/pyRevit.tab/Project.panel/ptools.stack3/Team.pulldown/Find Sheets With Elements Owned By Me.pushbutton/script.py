'''
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
'''
__doc__ = 'Lists all sheets containing elements currently "owned" by the user. "Owned" elements are the elements' \
          'by the user since the last synchronize and release.'

# __window__.Close()

from Autodesk.Revit.DB import WorksharingUtils, ElementId, FilteredElementCollector, ViewSheet, BuiltInCategory
from Autodesk.Revit.UI import TaskDialog

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

cl_sheets = FilteredElementCollector(doc)
sheetsnotsorted = cl_sheets.OfCategory(BuiltInCategory.OST_Sheets).WhereElementIsNotElementType().ToElements()
sheets = sorted(sheetsnotsorted, key=lambda x: x.SheetNumber)

filteredlist = []

if doc.IsWorkshared:
    print('Searching all sheets...\n')
    print('NAME      NUMBER')
    print('-'*100)
    for sheet in sheets:
        sheetisedited = False
        sheetviewlist = []
        sheetviewlist.append(sheet.Id)
        vportids = sheet.GetAllViewports()
        for vportid in vportids:
            sheetviewlist.append(doc.GetElement(vportid).ViewId)
        for view in sheetviewlist:
            curviewelements = FilteredElementCollector(doc).OwnedByView(view).WhereElementIsNotElementType().ToElements()
            if len(curviewelements) > 0:
                for el in curviewelements:
                    wti = WorksharingUtils.GetWorksharingTooltipInfo(doc, el.Id)
                    # wti.Creator, wti.Owner, wti.LastChangedBy
                    if wti.Owner == __revit__.Application.Username:
                        filteredlist.append(sheet)
                        print('{0}{1}'.format(sheet.LookupParameter('Sheet Number').AsString().ljust(10),
                                              sheet.LookupParameter('Sheet Name').AsString().ljust(50)
                                              ))
                        sheetisedited = True
                        break
            if sheetisedited:
                break
        else:
            pass
    print('\nAll done...')
else:
    TaskDialog.Show('pyrevit','Model is not workshared.')