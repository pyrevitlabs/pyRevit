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

# gtalarico@gmail.com

# All Credit to dp-stuff.org
# http://dp-stuff.org/revit-view-underlay-property-python-problem/

__doc__ = 'Removes Underlay from selected views.'

import clr
import math
clr.AddReference('RevitAPI')
clr.AddReference('RevitAPIUI')
from Autodesk.Revit.DB import *

doc = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument

selEls = uidoc.Selection.Elements

with Transaction(doc, 'Batch Set Underlay to None') as t:
    t.Start()
    for el in selEls:
        if (el.Category.Id.IntegerValue == int(BuiltInCategory.OST_Views)) and (el.CanBePrinted):
            p = el.get_Parameter(BuiltInParameter.VIEW_UNDERLAY_ID)
            if (p is not None):
                p.Set(ElementId.InvalidElementId)

    t.Commit()

__window__.Close()
