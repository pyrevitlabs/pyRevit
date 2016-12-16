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

__window__.Close()

import clr

from Autodesk.Revit.DB import Transaction, FilteredElementCollector, PrintRange, View, ViewSet, ViewSheetSet
from Autodesk.Revit.UI import TaskDialog

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

sheetsetname = 'ViewPrintSet_Derek'

# Get printmanager / viewsheetsetting
printmanager = doc.PrintManager
printmanager.PrintRange = PrintRange.Select
viewsheetsetting = printmanager.ViewSheetSetting

# Collect selected views
myviewset = ViewSet()
for elId in uidoc.Selection.GetElementIds():
    el = doc.GetElement(elId)
    if isinstance(el, View):
        myviewset.Insert(el)

if myviewset.IsEmpty:
    TaskDialog.Show('pyRevit', 'At least one viewport must be selected.')
else:
    # Collect existing sheet sets
    cl = FilteredElementCollector(doc)
    viewsheetsets = cl.OfClass(clr.GetClrType(ViewSheetSet)).WhereElementIsNotElementType().ToElements()
    allviewsheetsets = {vss.Name: vss for vss in viewsheetsets}

    with Transaction(doc, 'Create Print Set (Derek)') as t:
        t.Start()
        # Delete existing matching sheet set
        if sheetsetname in allviewsheetsets.keys():
            viewsheetsetting.CurrentViewSheetSet = allviewsheetsets[sheetsetname]
            viewsheetsetting.Delete()

        # Create new sheet set
        viewsheetsetting.CurrentViewSheetSet.Views = myviewset
        viewsheetsetting.SaveAs(sheetsetname)
        t.Commit()
