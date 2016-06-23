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

__doc__ = 'Lists all graphic styles in the model.'

from Autodesk.Revit.DB import FilteredElementCollector, GraphicsStyle, Transaction

doc = __revit__.ActiveUIDocument.Document

cl = FilteredElementCollector(doc)
gstyles = [i for i in cl.OfClass(GraphicsStyle).ToElements()]

for gs in gstyles:
    if gs.GraphicsStyleCategory.Parent:
        parent = gs.GraphicsStyleCategory.Parent.Name
    else:
        parent = '---'
    if gs.GraphicsStyleCategory.GetHashCode() > 0:
        print('NAME: {0} CATEGORY:{2} PARENT: {3} ID: {1}'.format(gs.Name.ljust(50), gs.Id, gs.GraphicsStyleCategory.Name.ljust(50), parent.ljust(50)))