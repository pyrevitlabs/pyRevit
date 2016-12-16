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

__doc__ = 'List all detail groups that include a text element inside them. This is helpful for spell checking.'

import clr
from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory, Element, Group, GroupType, Transaction, \
    BuiltInParameter, TextNote

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

cl = FilteredElementCollector(doc)
grps = list(cl.OfClass(clr.GetClrType(Group)).ToElements())

grpTypes = set()

for g in grps:
    mems = g.GetMemberIds()
    for el in mems:
        mem = doc.GetElement(el)
        if isinstance(mem, TextNote):
            grpTypes.add(g.GroupType.Id)

for gtId in grpTypes:
    print(Element.Name.GetValue(doc.GetElement(gtId)))
