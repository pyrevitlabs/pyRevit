"""
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
"""

__doc__ = 'Find all Rooms/Areas/Spaces with identical names to the select room, area or space and calculates ' \
          'the average area of that space type.'

from Autodesk.Revit.DB import FilteredElementCollector, ElementId, BuiltInCategory, Area
from Autodesk.Revit.DB.Architecture import Room
from Autodesk.Revit.DB.Mechanical import Space

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

selection = [doc.GetElement(elId) for elId in __revit__.ActiveUIDocument.Selection.GetElementIds()]

areas =  FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Areas).WhereElementIsNotElementType().ToElements()
rms =    FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Rooms).WhereElementIsNotElementType().ToElements()
spaces = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_MEPSpaces) \
                                      .WhereElementIsNotElementType().ToElements()

total = 0.0
average = 0.0
count = 0

for el in selection:
    if isinstance(el, Area):
        selareaname = el.LookupParameter('Name').AsString()
        print("AREA TYPE IS: {}".format(selareaname))
        for area in areas:
            areaname = area.LookupParameter('Name').AsString()
            if area.AreaScheme.Name == el.AreaScheme.Name and selareaname == areaname:
                total += area.LookupParameter('Area').AsDouble()
                count += 1
        print("TOTAL OF {} AREAS WERE FOUND.".format(count))
    elif isinstance(el, Room):
        selroomname = el.LookupParameter('Name').AsString()
        print("ROOM TYPE IS: {}".format(selroomname))
        for room in rms:
            roomname = room.LookupParameter('Name').AsString()
            if selroomname == roomname:
                total += room.LookupParameter('Area').AsDouble()
                count += 1
        print("TOTAL OF {} ROOMS WERE FOUND.".format(count))
    elif isinstance(el, Space):
        selspacename = el.LookupParameter('Name').AsString()
        print("SPACE TYPE IS: {}".format(selspacename))
        for space in spaces:
            spacename = space.LookupParameter('Name').AsString()
            if selspacename == spacename:
                total += space.LookupParameter('Area').AsDouble()
                count += 1
        print("TOTAL OF {} SPACES WERE FOUND.".format(count))

    average = total / count
    print("AVERAGE AREA OF THE SELECTED TYPE IS:\n{0} SQFT\n{1} ACRE".format(average, average / 43560))
