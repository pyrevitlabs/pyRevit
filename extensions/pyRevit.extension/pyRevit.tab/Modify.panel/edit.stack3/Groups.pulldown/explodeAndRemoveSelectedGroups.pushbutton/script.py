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

__doc__ = 'Explodes all instances of the selected groups and removes the group definition from project browser.'

__window__.Close()
import clr
from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory, Group, GroupType, Transaction, BuiltInParameter
from Autodesk.Revit.UI import TaskDialog

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
selection = [doc.GetElement(elId) for elId in __revit__.ActiveUIDocument.Selection.GetElementIds()]

t = Transaction(doc, 'Explode and Purge Selected Groups')
t.Start()

grpTypes = set()
grps = []
attachedGrps = []

for el in selection:
    if isinstance(el, GroupType):
        grpTypes.add(el)
    elif isinstance(el, Group):
        grpTypes.add(el.GroupType)

if len(grpTypes) == 0:
    TaskDialog.Show('pyrevit', 'At least one group type must be selected.')

for gt in grpTypes:
    for grp in gt.Groups:
        grps.append(grp)

for g in grps:
    if g.LookupParameter('Attached to'):
        attachedGrps.append(g.GroupType)
    g.UngroupMembers()

for agt in attachedGrps:
    doc.Delete(agt.Id)

for gt in grpTypes:
    doc.Delete(gt.Id)

t.Commit()
