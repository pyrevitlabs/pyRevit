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

__doc__ = 'Lists all Model Lines, Sketch Lines, and Detail Lines.'

from Autodesk.Revit.DB import ElementMulticategoryFilter, FilteredElementCollector, BuiltInCategory
from System.Collections.Generic import List

doc = __revit__.ActiveUIDocument.Document

# lists all sketch based objects as:
# 			ModelLine/ModelArc/ModelEllipse/...		<Sketch>
# lists all sketch based detail objects as:
# 			DetailLines/DetailArc/DetailEllipse/...		whatever_style_type_it_has

elfilter = ElementMulticategoryFilter(List[BuiltInCategory]([BuiltInCategory.OST_Lines, BuiltInCategory.OST_SketchLines]))
cl = FilteredElementCollector(doc)
cllines = cl.WherePasses(elfilter).WhereElementIsNotElementType().ToElements()

for c in cllines:
    print('{0:<10} {1:<25}{2:<8} {3:<15} {4:<20}'.format(c.Id, c.GetType().Name, c.LineStyle.Id, c.LineStyle.Name,
                                                         c.Category.Name))
