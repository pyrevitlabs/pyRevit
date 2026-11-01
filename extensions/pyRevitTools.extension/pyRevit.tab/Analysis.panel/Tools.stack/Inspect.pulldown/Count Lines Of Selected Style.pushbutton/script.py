# -*- coding: utf-8 -*-
"""Count all lines in the model with the line style of the selected lines.

Shift-click lists every matching line.
"""

from collections import OrderedDict

from pyrevit import script
from pyrevit import revit, DB, EXEC_PARAMS
from pyrevit.coreutils import applocales

from outputtext import escape_for_output

output = script.get_output()

RESOURCES = script.get_bundle_file("resources.xaml")


def _t(key):
    return applocales.get_locale_string_from_xaml(RESOURCES, key)


def collect_lines():
    return list(
        DB.FilteredElementCollector(revit.doc)
        .OfCategory(DB.BuiltInCategory.OST_Lines)
        .WhereElementIsNotElementType()
    )


def selected_line_styles():
    """Return the distinct line style names of the selected lines, in selection order."""
    style_names = OrderedDict()
    for element in revit.get_selection().elements:
        line_style = getattr(element, "LineStyle", None)
        if line_style:
            style_names[line_style.Name] = None
    return list(style_names)


def owner_view_name(line):
    view = revit.doc.GetElement(line.OwnerViewId)
    return escape_for_output(revit.query.get_name(view)) if view else _t("model")


def print_matching_lines(style_name, lines):
    output.print_table(
        table_data=[
            [output.linkify(line.Id), line.GetType().Name, owner_view_name(line)]
            for line in lines
        ],
        title=_t("lines_of_style").format(escape_for_output(style_name)),
        columns=[_t("column_line"), _t("column_class"), _t("column_view")],
    )


def main():
    style_names = selected_line_styles()
    if not style_names:
        output.print_md("**{}**".format(_t("select_lines")))
        return
    all_lines = collect_lines()
    lines_by_style = {
        style_name: [line for line in all_lines if line.LineStyle.Name == style_name]
        for style_name in style_names
    }
    output.print_table(
        table_data=[
            [escape_for_output(style_name), len(lines_by_style[style_name])]
            for style_name in style_names
        ],
        title=_t("table_title"),
        columns=[_t("column_style"), _t("column_count")],
    )
    if EXEC_PARAMS.config_mode:
        for style_name in style_names:
            print_matching_lines(style_name, lines_by_style[style_name])


if __name__ == "__main__":
    main()
