"""List sorted Detail Line Counts for all views with Detail Lines."""
from collections import defaultdict

from pyrevit import script
from pyrevit import revit, DB
from pyrevit.compat import get_elementid_value_func


__title__ = 'Lines Per View Counter'
__author__ = 'Frederic Beaupere'
__contact__ = 'https://github.com/frederic-beaupere'
__author2__ = 'Jean-Marc Couffin'
__contact2__ = 'https://github.com/jmcouffin'
__credits__ = 'http://eirannejad.github.io/pyRevit/credits/'

doc = revit.doc
output = script.get_output()
output.close_others()
output.set_width(800)


def line_count(document=doc):
    """
    Counts the number of detail lines in each view of a Revit document.

    Args:
        document (Document): The Revit document to count the lines in. Defaults to the active document.

    Returns:
        None
    """
    if document == doc:
        output.print_md("\n\n## LINE COUNT IN CURRENT DOCUMENT: "+ doc.Title+"\n")
    else:
        document = document.GetLinkDocument()
        l_title = document.Title.split(":")[0]
        output.print_md("\n\n## LINE COUNT IN REVIT LINK: "+ l_title+"\n")
    try:
        detail_lines = defaultdict(int)
        table_data = []
        lines = DB.FilteredElementCollector(document).OfCategory(DB.BuiltInCategory.OST_Lines).WhereElementIsNotElementType().ToElements()
        for line in lines:
            if line.CurveElementType.ToString() == "DetailCurve":
                get_elementid_value = get_elementid_value_func()
                view_id_int = get_elementid_value(line.OwnerViewId)
                detail_lines[view_id_int] += 1
        for line_count, view_id_int \
                in sorted(zip(detail_lines.values(), detail_lines.keys()),
                              reverse=True):
            view_id = DB.ElementId(view_id_int)
            view_creator = DB.WorksharingUtils.GetWorksharingTooltipInfo(document,view_id).Creator
            try:
                view_name = revit.query.get_name(document.GetElement(view_id))
            except Exception:
                view_name = "<no view name available>"
            table_data.append([line_count, view_name, output.linkify(view_id), view_creator])
        table_data.append([str(sum(detail_lines.values()))+" Lines in Total","In "+str(len(detail_lines))+" Views", "", ""])
        output.print_table(table_data,columns=["Number", 'Name', 'Id', 'Creator'], last_line_style='font-weight:bold;font-size:1.2em;')
    except Exception as e:
        output.print_md("**Error: {}**".format(e))

if __name__ == '__main__':
    output.print_md("\n\n# LINES PER VIEW IN CURRENT DOCUMENT\n___\n\n")
    line_count()
    if __shiftclick__:
        output.print_md("\n\n# LINES PER VIEW IN LINKS\n___\n\n")
        revit_links = DB.FilteredElementCollector(doc).OfClass(DB.RevitLinkInstance).ToElements()
        for link in revit_links:
            line_count(link)

output.print_md('By: [{}]({}) and some improvements from [{}]({})\n\n'.format(__author__, __contact__, __author2__, __contact2__))
