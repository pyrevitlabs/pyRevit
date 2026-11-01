# -*- coding: utf-8 -*-
"""List sorted Detail Line Counts for all views with Detail Lines.

Shift-click also counts the detail lines in every Revit link.
"""

from collections import defaultdict

from pyrevit import script
from pyrevit import revit, DB, EXEC_PARAMS
from pyrevit.compat import get_elementid_value_func
from pyrevit.coreutils import applocales

from outputtext import escape_for_output

logger = script.get_logger()
output = script.get_output()
output.close_others()
output.set_width(800)

RESOURCES = script.get_bundle_file("resources.xaml")


def _t(key):
    return applocales.get_locale_string_from_xaml(RESOURCES, key)


def count_detail_lines_per_view(document):
    """Return the number of detail lines of the document, keyed by owner view id."""
    get_elementid_value = get_elementid_value_func()
    counts = defaultdict(int)
    lines = (
        DB.FilteredElementCollector(document)
        .OfCategory(DB.BuiltInCategory.OST_Lines)
        .WhereElementIsNotElementType()
    )
    for line in lines:
        if line.CurveElementType == DB.CurveElementType.DetailCurve:
            counts[get_elementid_value(line.OwnerViewId)] += 1
    return counts


def view_row(document, view_id_value, line_count):
    view_id = DB.ElementId(view_id_value)
    view = document.GetElement(view_id)
    view_name = (
        escape_for_output(revit.query.get_name(view)) if view else _t("no_view_name")
    )
    row = [line_count, view_name, output.linkify(view_id)]
    if document.IsWorkshared:
        creator = DB.WorksharingUtils.GetWorksharingTooltipInfo(
            document, view_id
        ).Creator
        row.append(escape_for_output(creator))
    return row


def report(document, heading):
    counts = count_detail_lines_per_view(document)
    output.print_md("## {}".format(heading))
    if not counts:
        output.print_md("**{}**".format(_t("no_detail_lines")))
        return
    rows = [
        view_row(document, view_id_value, line_count)
        for view_id_value, line_count in sorted(
            counts.items(), key=lambda item: item[1], reverse=True
        )
    ]
    columns = [_t("column_number"), _t("column_name"), _t("column_id")]
    if document.IsWorkshared:
        columns.append(_t("column_creator"))
    totals = [
        _t("lines_in_total").format(sum(counts.values())),
        _t("in_views").format(len(counts)),
    ]
    rows.append(totals + [""] * (len(columns) - len(totals)))
    output.print_table(
        rows,
        columns=columns,
        last_line_style="font-weight:bold;font-size:1.2em;",
    )


def report_links():
    output.print_md("# {}".format(_t("lines_in_links")))
    links = DB.FilteredElementCollector(revit.doc).OfClass(DB.RevitLinkInstance)
    for link in links:
        link_document = link.GetLinkDocument()
        if not link_document:
            logger.warning("Revit link {} is not loaded.".format(link.Name))
            continue
        report(
            link_document,
            _t("line_count_in_link").format(
                escape_for_output(link_document.Title.split(":")[0])
            ),
        )


def main():
    output.print_md("# {}".format(_t("lines_per_view")))
    report(
        revit.doc,
        _t("line_count_in_document").format(escape_for_output(revit.doc.Title)),
    )
    if EXEC_PARAMS.config_mode:
        report_links()


if __name__ == "__main__":
    main()
