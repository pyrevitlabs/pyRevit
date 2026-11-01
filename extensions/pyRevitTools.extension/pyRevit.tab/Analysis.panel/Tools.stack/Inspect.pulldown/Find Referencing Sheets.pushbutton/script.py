# -*- coding: utf-8 -*-
"""Find all sheets referencing the current view.

Especially useful for finding legends.
"""

from pyrevit import script
from pyrevit import revit, DB
from pyrevit.coreutils import applocales

from outputtext import escape_for_output

output = script.get_output()

RESOURCES = script.get_bundle_file("resources.xaml")


def _t(key):
    return applocales.get_locale_string_from_xaml(RESOURCES, key)


def placed_view_ids(sheet):
    """Return the ids of the views placed on the sheet, schedules included."""
    view_ids = {
        revit.doc.GetElement(viewport_id).ViewId
        for viewport_id in sheet.GetAllViewports()
    }
    sheet_elements = (
        DB.FilteredElementCollector(revit.doc)
        .OwnedByView(sheet.Id)
        .WhereElementIsNotElementType()
    )
    for element in sheet_elements:
        if isinstance(element, DB.ScheduleSheetInstance):
            view_ids.add(element.ScheduleId)
    return view_ids


def sheet_row(sheet):
    return [
        escape_for_output(sheet.SheetNumber),
        escape_for_output(sheet.Name),
        output.linkify(sheet.Id),
    ]


def main():
    current_view = revit.active_view
    sheets = revit.query.get_sheets(include_placeholders=False)
    referencing_sheets = [
        sheet for sheet in sheets if current_view.Id in placed_view_ids(sheet)
    ]
    output.print_md(
        "### {}".format(
            _t("sheets_referencing").format(
                escape_for_output(current_view.Name), output.linkify(current_view.Id)
            )
        )
    )
    if not referencing_sheets:
        output.print_md("**{}**".format(_t("no_sheets")))
        return
    output.print_table(
        table_data=[sheet_row(sheet) for sheet in referencing_sheets],
        title=_t("table_title").format(len(referencing_sheets)),
        columns=[_t("column_number"), _t("column_name"), _t("column_show")],
    )


if __name__ == "__main__":
    main()
