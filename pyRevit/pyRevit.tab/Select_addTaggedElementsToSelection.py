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

__doc__ = 'Select a series of tags and this tool will add their associated elements to selection. ' \
          'This is especially useful for isolating elements and their tags.'

__window__.Close()

from Autodesk.Revit.DB import ElementId, IndependentTag
from Autodesk.Revit.DB.Architecture import RoomTag
from Autodesk.Revit.UI import TaskDialog
from System.Collections.Generic import List

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
selection = list(uidoc.Selection.GetElementIds())

tagged_elements = []

for eltid in selection:
    elt = doc.GetElement(eltid)
    if isinstance(elt, IndependentTag):
        tagged_elements.append(elt.TaggedLocalElementId)

if len(tagged_elements) > 0:
    uidoc.Selection.SetElementIds(List[ElementId](selection + tagged_elements))
else:
    TaskDialog.Show('pyRevit', 'Please select at least one element tag.')