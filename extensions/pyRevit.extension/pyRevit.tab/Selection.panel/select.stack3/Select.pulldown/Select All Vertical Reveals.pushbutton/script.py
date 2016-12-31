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

__doc__ = 'Selects all vertical reveals in the project.'


__window__.Close()
from Autodesk.Revit.DB import FilteredElementCollector, ElementId, BuiltInCategory
from System.Collections.Generic import List

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

cl = FilteredElementCollector(doc)
revealslist = cl.OfCategory(BuiltInCategory.OST_Reveals).WhereElementIsNotElementType().ToElements()

selSet = []

for el in revealslist:
    if el.GetWallSweepInfo().IsVertical:
        selSet.append(el.Id)

uidoc.Selection.SetElementIds(List[ElementId](selSet))
