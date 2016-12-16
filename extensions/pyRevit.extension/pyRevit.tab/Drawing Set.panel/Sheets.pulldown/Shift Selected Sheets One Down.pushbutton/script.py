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

__doc__ = 'Increases the sheet number of the selected sheets by one.'

from Autodesk.Revit.DB import Transaction

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
selection = [doc.GetElement(elId) for elId in __revit__.ActiveUIDocument.Selection.GetElementIds()]

t = Transaction(doc, 'Shift Sheets')
t.Start()

shift = -1

selectedSheets = []
for elId in uidoc.Selection.GetElementIds():
    selectedSheets.append(doc.GetElement(elId))

sheetList = sorted(selectedSheets, key=lambda sheet: int(sheet.ParametersMap['Sheet Number'].AsString()[1:]))

if shift >= 0:
    sheetList.reverse()

for el in sheetList:  # uidoc.Selection.Elements.ReverseIterator()
    sheetNumber = el.LookupParameter('Sheet Number').AsString()
    sCat = sheetNumber[0:1]
    sNum = int(sheetNumber[1:])
    newName = str(sCat + '{0:03}'.format(sNum + shift))
    print sheetNumber + '\t -> \t' + newName
    el.LookupParameter('Sheet Number').Set(newName)

t.Commit()

# __window__.Close()
