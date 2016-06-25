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

__doc__ = 'Activates selection tool that picks only Grid elements.'

__window__.Close()
from Autodesk.Revit.UI.Selection import ISelectionFilter
from System.Collections.Generic import List
from Autodesk.Revit.DB import ElementId

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document


class PickByCategorySelectionFilter(ISelectionFilter):
    def __init__(self, catname):
        self.category = catname

    # standard API override function
    def AllowElement(self, element):
        if self.category in element.Category.Name:
            return True
        else:
            return False

    # standard API override function
    def AllowReference(self, refer, point):
        return False


def pickbycategory(catname):
    sel = PickByCategorySelectionFilter(catname)
    sellist = uidoc.Selection.PickElementsByRectangle(sel)
    filteredlist = []
    for el in sellist:
        filteredlist.append(el.Id)
    uidoc.Selection.SetElementIds(List[ElementId](filteredlist))


pickbycategory("Grid")
