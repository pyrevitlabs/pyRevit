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

__doc__ = 'Select a revision cloud and this tool will list all the sheets revised under the same revision.'

from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory, RevisionCloud, ElementId

doc = __revit__.ActiveUIDocument.Document

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
selection = [doc.GetElement(elId) for elId in __revit__.ActiveUIDocument.Selection.GetElementIds()]

selectedrevs = []
hasSelectedRevision = False
multipleRevs = False

for s in selection:
    if isinstance(s, RevisionCloud):
        selectedrevs.append(s.RevisionId.IntegerValue)

if len(selectedrevs) > 1:
    multipleRevs = True

print('REVISED SHEETS:\n\nNAME\tNUMBER\n--------------------------------------------------------------------------')
cl_sheets = FilteredElementCollector(doc)
sheetsnotsorted = cl_sheets.OfCategory(BuiltInCategory.OST_Sheets).WhereElementIsNotElementType().ToElements()
sheets = sorted(sheetsnotsorted, key=lambda x: x.SheetNumber)

for s in sheets:
    hasSelectedRevision = False
    revs = s.GetAllRevisionIds()
    revIds = [x.IntegerValue for x in revs]
    for sr in selectedrevs:
        if sr in revIds:
            hasSelectedRevision = True
    if hasSelectedRevision:
        print('{0}\t{1}'.format(s.LookupParameter('Sheet Number').AsString(),
                                s.LookupParameter('Sheet Name').AsString()
                                ))
        if multipleRevs:
            for rev in revs:
                rev = doc.GetElement(rev)
                print('\tREV#: {0}\t\tDATE: {1}\t\tDESC:{2}'.format(rev.RevisionNumber,
                                                                    rev.RevisionDate,
                                                                    rev.Description
                                                                    ))
