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

__doc__ = 'Lists all lines in the model with matching style to the selected line.'

from Autodesk.Revit.DB import *
import Autodesk.Revit.UI

doc = __revit__.ActiveUIDocument.Document
selection = [doc.GetElement(elId) for elId in __revit__.ActiveUIDocument.Selection.GetElementIds()]

selectedStyle = None

if len(selection) > 0:
    el = selection[0]
    selectedStyle = el.LineStyle

# lists all sketch based objects as:
#           ModelLine/ModelArc/ModelEllipse/...		<Sketch>
# lists all sketch based detail objects as:
# 			DetailLines/DetailArc/DetailEllipse/...		whatever_style_type_it_has
cl = FilteredElementCollector(doc)
cllines = cl.OfCategory(BuiltInCategory.OST_Lines or BuiltInCategory.OST_SketchLines).WhereElementIsNotElementType()
for c in cllines:
    if c.LineStyle.Name == selectedStyle.Name:
        print('{0:<10} {1:<25}{2:<8} {3:<15}'.format(c.Id, c.GetType().Name, c.LineStyle.Id, c.LineStyle.Name))
