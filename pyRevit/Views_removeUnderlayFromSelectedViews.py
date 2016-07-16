"""
Copyright (c) 2014-2016 gtalarico@gmail.com
Python scripts for Autodesk Revit
TESTED API: 2015 | 2016

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

# Original Code by dp-stuff.org
# http://dp-stuff.org/revit-view-underlay-property-python-problem/

__doc__ = 'Removes Underlay From Selected Views.'

import clr
clr.AddReference('RevitAPI')
clr.AddReference('RevitAPIUI')
from Autodesk.Revit.UI import TaskDialog
from Autodesk.Revit.DB import Transaction
from Autodesk.Revit.DB import ElementId
from Autodesk.Revit.DB import BuiltInParameter, BuiltInCategory

doc = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument

selection = uidoc.Selection
selection_ids = selection.GetElementIds()

if selection_ids.Count > 0:
    t = Transaction(doc, 'Batch Set Underlay to None')
    t.Start()

    for element_id in selection_ids:
        element = doc.GetElement(element_id)
        if element.Category.Id.IntegerValue == int(BuiltInCategory.OST_Views) \
                and (element.CanBePrinted):
            p = element.get_Parameter(BuiltInParameter.VIEW_UNDERLAY_ID)
            if p is not None:
                p.Set(ElementId.InvalidElementId)

    t.Commit()
else:
    TaskDialog.Show('Remove Underlay', 'Select Views to Remove Underlay')

__window__.Close()
