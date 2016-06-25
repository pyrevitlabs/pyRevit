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

__doc__ = 'Tags all the spaces in all the views with the default space tag.'

from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory, LinkElementId, UV, XYZ, Transaction, \
    ViewSection, View3D, ViewDrafting, ViewSheet

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

cl_views = FilteredElementCollector(doc)
views = cl_views.OfCategory(BuiltInCategory.OST_Views).WhereElementIsNotElementType().ToElements()
cl_rooms = FilteredElementCollector(doc)
spaces = cl_rooms.OfCategory(BuiltInCategory.OST_MEPSpaces).WhereElementIsNotElementType().ToElements()


def getelementcenter(el, v):
    cen = el.Location.Point
    z = (el.UpperLimit.Elevation + el.LimitOffset) / 2
    cen = cen.Add(XYZ(0, 0, z))
    return cen


t = Transaction(doc, 'Tag All Spaces in All Views')
t.Start()

for v in views:
    for el in spaces:
        loc = getelementcenter(el, v)
        if isinstance(v, View3D) or isinstance(v, ViewDrafting) or isinstance(v, ViewSheet):
            continue
        else:
            spacetag = doc.Create.NewSpaceTag(el, UV(loc.X, loc.Y), v)
            if isinstance(v, ViewSection):
                spacetag.Location.Move(XYZ(0, 0, loc.Z))

t.Commit()
