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

__doc__ = 'List all groups that includethe selected group element as a nested group.'

import clr
from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory, Element, Group, GroupType, Transaction

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
selection = list(uidoc.Selection.GetElementIds())

cl = FilteredElementCollector(doc)
grps = list(cl.OfClass(clr.GetClrType(Group)).ToElements())

grpTypes = set()

if len(selection) > 0:
    elid = selection.pop()
    el = doc.GetElement(elid)
    if isinstance(el, Group):
        selectedgtid = el.GroupType.Id
        for g in grps:
            mems = g.GetMemberIds()
            for memid in mems:
                mem = doc.GetElement(memid)
                if isinstance(mem, Group):
                    memgtid = mem.GroupType.Id
                    if memgtid == selectedgtid:
                        grpTypes.add(g.GroupType.Id)

        for gtId in grpTypes:
            print(Element.Name.GetValue(doc.GetElement(gtId)))

else:
    pass