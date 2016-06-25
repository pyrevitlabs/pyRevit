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

__doc__ = 'Lists all viewport types in this model.'

from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory, Element, ElementType

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

vps = []

cl_views = FilteredElementCollector(doc)
vptypes = cl_views.OfClass(ElementType).ToElements()

for tp in vptypes:
    if tp.FamilyName == 'Viewport':
        print('ID: {1} TYPE: {0}'.format(Element.Name.GetValue(tp),
                                         str(tp.Id).ljust(10)
                                         ))
