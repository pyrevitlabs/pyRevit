"""
Lines per view counter
Lists sorted Detail Line Counts for all views with Detail Lines.

Copyright (c) 2017 Frederic Beaupere
github.com/frederic-beaupere

--------------------------------------------------------
PyRevit Notice:
Copyright (c) 2014-2017 Ehsan Iran-Nejad
pyRevit: repository at https://github.com/eirannejad/pyRevit

"""

__title__ = 'Lines per view counter'
__author__ = 'Frederic Beaupere'
__contact__ = 'github.com/frederic-beaupere'
__credits__ = 'http://eirannejad.github.io/pyRevit/credits/'
__doc__ = """Lists sorted Detail Line Counts for all views with Detail Lines."""

import clr
clr.AddReference("RevitAPI")
import Autodesk
from Autodesk.Revit.DB import FilteredElementCollector as fec
from Autodesk.Revit.DB import BuiltInCategory
from Autodesk.Revit.DB import ElementId
from Autodesk.Revit.DB import WorksharingUtils
from revitutils import doc
from collections import defaultdict

detail_lines = defaultdict(int)
all_lines = fec(doc).OfCategory(BuiltInCategory.OST_Lines).WhereElementIsNotElementType().ToElements()

for line in all_lines:
    if line.CurveElementType.ToString() == "DetailCurve":
        view_id_int = line.OwnerViewId.IntegerValue
        detail_lines[view_id_int] += 1

print(9 * "_" + "Line count per view: ")

for line_count, view_id_int in sorted(zip(detail_lines.values(), detail_lines.keys()), reverse=True):
    view_id = ElementId(view_id_int)
    view_creator = WorksharingUtils.GetWorksharingTooltipInfo(doc, view_id).Creator
    
    if doc.GetElement(view_id).Name:
        view_name = doc.GetElement(view_id).Name
    else:
        view_name = "no view name available"
    
    print("{0} Lines in view id:{1} from view creator: {2} view name: {3}".format(
        str(line_count).rjust(7),
        str(view_id_int).rjust(9),
        view_creator.ljust(15),
        view_name.ljust(60)))

print("\n" + str(sum(detail_lines.values())) + " Lines in " + str(len(detail_lines)) + " Views.")
