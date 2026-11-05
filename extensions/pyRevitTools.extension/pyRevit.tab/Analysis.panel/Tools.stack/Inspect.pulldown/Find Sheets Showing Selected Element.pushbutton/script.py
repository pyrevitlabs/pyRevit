# -*- coding: utf-8 -*-
"""List all sheets and views that the selected elements are visible in."""

from collections import OrderedDict

from pyrevit import script
from pyrevit import revit, DB
from pyrevit.coreutils import applocales, escape_for_output

output = script.get_output()

RESOURCES = script.get_bundle_file("resources.xaml")


def _t(key):
    return applocales.get_locale_string_from_xaml(RESOURCES, key)


def collect_sheets():
    sheets = (
        DB.FilteredElementCollector(revit.doc)
        .OfCategory(DB.BuiltInCategory.OST_Sheets)
        .WhereElementIsNotElementType()
    )
    return sorted(sheets, key=lambda sheet: sheet.SheetNumber)


def shows_selection(viewport, view, selected_ids):
    """Tell whether the viewport is selected or its view contains a selected element."""
    if viewport.Id in selected_ids:
        return True
    view_element_ids = set(
        DB.FilteredElementCollector(revit.doc, view.Id)
        .WhereElementIsNotElementType()
        .ToElementIds()
    )
    return not view_element_ids.isdisjoint(selected_ids)


def find_showing_viewports(sheets, selected_ids):
    """Map each sheet to the (viewport, view) pairs that show a selected element."""
    viewports_by_sheet = OrderedDict()
    for sheet in sheets:
        for viewport_id in sheet.GetAllViewports():
            viewport = revit.doc.GetElement(viewport_id)
            view = revit.doc.GetElement(viewport.ViewId)
            if shows_selection(viewport, view, selected_ids):
                viewports_by_sheet.setdefault(sheet, []).append((viewport, view))
    return viewports_by_sheet


def main():
    selected_ids = set(revit.get_selection().element_ids)
    viewports_by_sheet = find_showing_viewports(collect_sheets(), selected_ids)
    output.print_md("### {}".format(_t("sheets_containing")))
    if not viewports_by_sheet:
        output.print_md("**{}**".format(_t("no_sheets")))
        return
    output.print_table(
        table_data=[
            [
                escape_for_output(sheet.SheetNumber),
                escape_for_output(sheet.Name),
                output.linkify(sheet.Id),
                escape_for_output(revit.query.get_name(view)),
                output.linkify(viewport.Id),
            ]
            for sheet, viewports in viewports_by_sheet.items()
            for viewport, view in viewports
        ],
        title=_t("table_title"),
        columns=[
            _t("column_number"),
            _t("column_sheet"),
            _t("column_sheet_show"),
            _t("column_view"),
            _t("column_viewport_show"),
        ],
    )


if __name__ == "__main__":
    main()
