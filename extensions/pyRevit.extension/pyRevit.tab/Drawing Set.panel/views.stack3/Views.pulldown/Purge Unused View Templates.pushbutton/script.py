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

__doc__ = 'Deletes all unused view templates (Any view template that has not been assigned to a view).'

__window__.Width = 1100
from Autodesk.Revit.DB import FilteredElementCollector, Transaction, BuiltInCategory, ElementId
from Autodesk.Revit.UI import TaskDialog, TaskDialogCommonButtons, TaskDialogResult

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
viewlist = FilteredElementCollector(doc).OfCategory(
    BuiltInCategory.OST_Views).WhereElementIsNotElementType().ToElements()

vtemp = set()
usedvtemp = set()
views = []

for v in viewlist:
    if v.IsTemplate and 'master' not in v.ViewName.lower():
        vtemp.add(v.Id.IntegerValue)
    else:
        views.append(v)

for v in views:
    vtid = v.ViewTemplateId.IntegerValue
    if vtid > 0:
        usedvtemp.add(vtid)

unusedvtemp = vtemp - usedvtemp

t = Transaction(doc, 'Purge Unused View Templates')
t.Start()

for vid in unusedvtemp:
    view = doc.GetElement(ElementId(vid))
    print view.ViewName

res = TaskDialog.Show('pyrevit',
                      'Are you sure you want to remove these view templates?',
                      TaskDialogCommonButtons.Yes | TaskDialogCommonButtons.Cancel)

if res == TaskDialogResult.Yes:
    for v in unusedvtemp:
        doc.Delete(ElementId(v))
else:
    print('----------- Purge Cancelled --------------')

t.Commit()
