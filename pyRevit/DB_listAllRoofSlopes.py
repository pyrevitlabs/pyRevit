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

__doc__ = 'Lists all roof slopes in the model.'

__window__.Text += ': List of all roof slopes in the model'

from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

rooflist = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Roofs).WhereElementIsNotElementType().ToElements()

slopes = dict()

for el in rooflist:
    p = el.LookupParameter('Slope')
    if p:
        s = p.AsValueString()
        if s in slopes.keys():
            slopes[s].append(el.Id.IntegerValue)
        else:
            slopes[s] = [el.Id.IntegerValue]

for sl, elid in slopes.items():
    print('SLOPE: {0}'.format(sl))
    print('ROOF ELEMENTS WITH THIS SLOPE:')
    print(elid)
    print('\n')
