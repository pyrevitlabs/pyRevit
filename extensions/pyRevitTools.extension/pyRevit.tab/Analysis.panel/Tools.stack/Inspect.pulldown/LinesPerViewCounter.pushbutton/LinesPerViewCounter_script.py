"""List sorted Detail Line Counts for all views with Detail Lines."""
from collections import defaultdict

from pyrevit import script
from pyrevit import revit, DB


__title__ = 'Lines Per View Counter'
__author__ = 'Frederic Beaupere'
__contact__ = 'https://github.com/frederic-beaupere'
__credits__ = 'http://eirannejad.github.io/pyRevit/credits/'



output = script.get_output()


detail_lines = defaultdict(int)
all_lines = DB.FilteredElementCollector(revit.doc)\
            .OfCategory(DB.BuiltInCategory.OST_Lines)\
            .WhereElementIsNotElementType()\
            .ToElements()

for line in all_lines:
    if line.CurveElementType.ToString() == "DetailCurve":
        view_id_int = line.OwnerViewId.IntegerValue
        detail_lines[view_id_int] += 1

output.print_md("####LINE COUNT IN CURRENT VIEW:")
output.print_md('By: [{}]({})'.format(__author__, __contact__))

for line_count, view_id_int \
        in sorted(zip(detail_lines.values(), detail_lines.keys()),
                  reverse=True):
    view_id = DB.ElementId(view_id_int)
    view_creator = \
        DB.WorksharingUtils.GetWorksharingTooltipInfo(revit.doc,
                                                      view_id).Creator

    try:
        view_name = revit.query.get_name(revit.doc.GetElement(view_id))
    except Exception:
        view_name = "<no view name available>"

    output.print_md("\n**{0} Lines in view:** {3}\n"
                    "View id:{1}\n"
                    "View creator: {2}\n".format(line_count,
                                                 output.linkify(view_id),
                                                 view_creator,
                                                 view_name))

print("\n"
      + str(sum(detail_lines.values()))
      + " Lines in "
      + str(len(detail_lines))
      + " Views.")
