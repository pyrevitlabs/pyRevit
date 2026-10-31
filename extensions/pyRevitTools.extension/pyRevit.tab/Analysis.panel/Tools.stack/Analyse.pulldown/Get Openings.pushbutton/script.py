# -*- coding: utf-8 -*-
"""Lists all openings in the project and creates
a selection filter for them.
"""

import time

from pyrevit import script
from pyrevit import revit, DB
from pyrevit.compat import get_elementid_value_func
from pyrevit.coreutils import applocales, escape_for_html
from pyrevit.framework import List
from pyrevit.revit import query

output = script.get_output()

RESOURCES = script.get_bundle_file("resources.xaml")
OPENING_FILTER_NAME = "0_ShaftOpenings"
OPENING_CATEGORIES = [
    DB.BuiltInCategory.OST_FloorOpening,
    DB.BuiltInCategory.OST_SWallRectOpening,
    DB.BuiltInCategory.OST_ShaftOpening,
    DB.BuiltInCategory.OST_RoofOpening,
]


def _t(key):
    return applocales.get_locale_string_from_xaml(RESOURCES, key)


def sync_opening_filter():
    """Create the selection filter for all openings, or add them to the existing one.

    Returns:
        bool: True if the filter was created, False if an existing one was updated.
    """
    opening_ids = List[DB.ElementId](
        DB.FilteredElementCollector(revit.doc).OfClass(DB.Opening).ToElementIds()
    )
    existing_filters = {
        selection_filter.Name: selection_filter
        for selection_filter in DB.FilteredElementCollector(revit.doc).OfClass(
            DB.SelectionFilterElement
        )
    }
    with revit.Transaction(_t("transaction_name")):
        created = OPENING_FILTER_NAME not in existing_filters
        if created:
            opening_filter = DB.SelectionFilterElement.Create(
                revit.doc, OPENING_FILTER_NAME
            )
        else:
            opening_filter = existing_filters[OPENING_FILTER_NAME]
        opening_filter.AddSet(opening_ids)
    return created


def report(openings):
    output.print_md("#### {}".format(_t("openings_in_project").format(len(openings))))
    if not openings:
        return
    get_elementid_value = get_elementid_value_func()
    output.print_table(
        table_data=[
            [
                escape_for_html(opening.Name),
                get_elementid_value(opening.Id),
                output.linkify(opening.Id),
            ]
            for opening in openings
        ],
        title=_t("table_title"),
        columns=[_t("column_name"), _t("column_id"), _t("column_show")],
    )


started = time.time()
openings = query.get_elements_by_categories(OPENING_CATEGORIES)
filter_message = "created_filter" if sync_opening_filter() else "updated_filter"
output.print_md(_t(filter_message).format(OPENING_FILTER_NAME))
report(openings)
output.print_md("---")
output.print_md("#### {}".format(_t("finished_in").format(time.time() - started)))
