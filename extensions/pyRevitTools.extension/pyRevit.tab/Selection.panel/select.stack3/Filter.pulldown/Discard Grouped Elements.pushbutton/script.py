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

__doc__ = 'Discards (not delete) grouped elements from the current selection.'

from Autodesk.Revit.DB import ElementId, Group
from System.Collections.Generic import List

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

__context__ = 'Selection'

set = []
for elId in uidoc.Selection.GetElementIds():
    el = doc.GetElement(elId)
    if el.GroupId == ElementId.InvalidElementId and not isinstance(el, Group):
        set.append(elId)

uidoc.Selection.SetElementIds(List[ElementId](set))
uidoc.RefreshActiveView()
