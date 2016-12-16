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

__doc__ = 'Finds and lists rooms with identical numbers.'

import collections

from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory, ElementId, Element
from Autodesk.Revit.UI import TaskDialog
from System.Collections.Generic import List

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

curview = uidoc.ActiveGraphicalView

rooms = FilteredElementCollector(doc, curview.Id).OfCategory(
    BuiltInCategory.OST_Rooms).WhereElementIsNotElementType().ToElementIds()

roomnums = [doc.GetElement(rmid).Number for rmid in rooms]
duplicates = [item for item, count in collections.Counter(roomnums).items() if count > 1]

if len(duplicates) > 0:
    for rn in duplicates:
        print('IDENTICAL ROOM NUMBER:  {}'.format(rn))
        for rmid in rooms:
            rm = doc.GetElement(rmid)
            if rm.Number == rn:
                print('\tROOM NAME:  {} LEVEL: {}'.format(rm.LookupParameter('Name').AsString().ljust(30), rm.Level.Name))
        print('\n')
else:
    print('No identical room numbers were found.')