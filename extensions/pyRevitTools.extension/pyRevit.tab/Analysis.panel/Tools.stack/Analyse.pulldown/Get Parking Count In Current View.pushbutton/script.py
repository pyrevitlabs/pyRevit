# -*- coding: utf-8 -*-
"""Get a total count and types of parking elements in the current view."""

from collections import Counter

from pyrevit import script
from pyrevit import revit, DB
from pyrevit.coreutils import applocales, escape_for_html
from pyrevit.revit import query

output = script.get_output()

RESOURCES = script.get_bundle_file("resources.xaml")


def _t(key):
    return applocales.get_locale_string_from_xaml(RESOURCES, key)


def escape_for_output(text):
    escaped = escape_for_html(text)
    for character in "|*_`[":
        escaped = escaped.replace(character, "&#{};".format(ord(character)))
    return escaped


def type_name_of(element):
    element_type = revit.doc.GetElement(element.GetTypeId())
    return query.get_name(element_type) if element_type else _t("unknown_type")


parking_elements = query.get_elements_by_categories(
    [DB.BuiltInCategory.OST_Parking], view_id=revit.active_view.Id
)
counts_by_type = Counter(type_name_of(element) for element in parking_elements)

output.print_md("### {}".format(_t("parking_count").format(len(parking_elements))))
if counts_by_type:
    output.print_table(
        table_data=[
            [escape_for_output(type_name), counts_by_type[type_name]]
            for type_name in sorted(counts_by_type)
        ],
        title=_t("table_title"),
        columns=[_t("column_type"), _t("column_count")],
    )
