"""
Copyright (c) 2014-2016 Gui Talarico
Written for pyRevit
TESTED API: 2015 | 2016

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

__doc__ = "Selects All Door Instances that have been Mirrored."

import clr

clr.AddReference('RevitAPI')
clr.AddReference('RevitAPIUI')
clr.AddReference("System")

from Autodesk.Revit.UI import TaskDialog
from Autodesk.Revit.DB import FilteredElementCollector
from Autodesk.Revit.DB import BuiltInCategory, ElementId
from System.Collections.Generic import List
# Required for collection

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

__window__.Close()

collector = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Doors)
doors = collector.ToElements()

mir_doors = []

for door in doors:
    try:
        if door.Mirrored:
            mir_doors.append(door)
    except AttributeError:
        pass  # foor Symbols that don't have Mirrored attribute.

TaskDialog.Show("Mirrored Doors", "Mirrored: {} of {} Doors".format(
                len(mir_doors), len(doors)))

# SELECT MIRRORED DOORS                 | 2015 + 2016 API
selection = uidoc.Selection
collection = List[ElementId]([door.Id for door in mir_doors])
selection.SetElementIds(collection)

# selection = uidoc.Selection.Elements  | 2015 API
# for door in mir_doors:                | 2015 API
    # selection.Add(door)               | 2015 API
