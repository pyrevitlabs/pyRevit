"""
Copyright (c) 2014-2016 gtalarico@gmail.com
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

__doc__ = 'Selects all mirrored doors in the model.'

# gtalarico@gmail.com

# TODO: Improve Task Dialog Stats
# Add Prompt: Select Doors?

import clr
clr.AddReference('RevitAPI')
clr.AddReference('RevitAPIUI')

from Autodesk.Revit.DB import FilteredElementCollector
from Autodesk.Revit.DB import BuiltInCategory
from Autodesk.Revit.UI import TaskDialog

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

collector = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Doors)
doors = collector.ToElements()

mir_doors = []
all_doors = []

for i in doors:
    try:
        all_doors.append(i)
        if i.Mirrored:
            mir_doors.append(i)
    except:
        pass

qty_mir_doors = len(mir_doors)
qty_doors = len(all_doors)

selection = uidoc.Selection.Elements

__window__.Close()

TaskDialog.Show("Mirrored doors Have been selected.", \
                "Mirrored Doors: {} of {}".format(str(qty_mir_doors), str(qty_doors)))

for door in mir_doors:
    selection.Add(door)
