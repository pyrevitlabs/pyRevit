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

__doc__ = 'Get a total count and types of parking elements in the current view.'

from Autodesk.Revit.DB import FilteredElementCollector, Transaction, BuiltInCategory, Element
from System.Collections.Generic import List

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

curview = uidoc.ActiveGraphicalView
parkings = FilteredElementCollector(doc, curview.Id).OfCategory(
    BuiltInCategory.OST_Parking).WhereElementIsNotElementType().ToElementIds()

print('PARKING COUNT: {0}'.format(len(list(parkings))))

ptypesdic = {}

for pid in parkings:
    ptype = doc.GetElement(doc.GetElement(pid).GetTypeId())
    ptname = Element.Name.GetValue(ptype)
    if ptname in ptypesdic:
        ptypesdic[ptname] += 1
    else:
        ptypesdic[ptname] = 1

print('PARKING TYPES AND COUNTS')
for ptname, ptcount in ptypesdic.items():
    print('TYPE: {0}COUNT: {1}'.format(ptname.ljust(35), ptcount))
