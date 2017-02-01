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

__title__ = 'Lines Per View Counter'
__author__ = 'Frederic Beaupere'
__contact__ = 'https://github.com/frederic-beaupere'
__credits__ = 'http://eirannejad.github.io/pyRevit/credits/'

__doc__ = 'Lists sorted Detail Line Counts for all views with Detail Lines.'

import clr
from collections import defaultdict

from scriptutils import print_md
from revitutils import doc

clr.AddReference("RevitAPI")

# noinspection PyUnresolvedReferences
from Autodesk.Revit.DB import FilteredElementCollector as Fec
# noinspection PyUnresolvedReferences
from Autodesk.Revit.DB import BuiltInCategory, ElementId, WorksharingUtils


detail_lines = defaultdict(int)
all_lines = Fec(doc).OfCategory(BuiltInCategory.OST_Lines).WhereElementIsNotElementType().ToElements()

for line in all_lines:
    if line.CurveElementType.ToString() == "DetailCurve":
        view_id_int = line.OwnerViewId.IntegerValue
        detail_lines[view_id_int] += 1

print_md("####LINE COUNT IN CURRENT VIEW:")
print_md('By: [{}]({})'.format(__author__, __contact__))

for line_count, view_id_int in sorted(zip(detail_lines.values(), detail_lines.keys()), reverse=True):
    view_id = ElementId(view_id_int)
    view_creator = WorksharingUtils.GetWorksharingTooltipInfo(doc, view_id).Creator

    try:
        view_name = doc.GetElement(view_id).ViewName
    except:
        view_name = "<no view name available>"

    print_md("\n**{0} Lines in view:** {3}\n"    \
             "View id:{1}\n"                     \
             "View creator: {2}\n".format(line_count, make_id_url(view_id_int), view_creator, view_name))

print("\n" + str(sum(detail_lines.values())) + " Lines in " + str(len(detail_lines)) + " Views.")
