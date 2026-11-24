# -*- coding: utf-8 -*-
"""List the selected elements as clickable links in the output window."""

from pyrevit import forms, script
from pyrevit import revit
from pyrevit.coreutils import applocales, escape_for_output

output = script.get_output()

RESOURCES = script.get_bundle_file("resources.xaml")
SELECT_ALL_LINK_LIMIT = 2000


def _t(key):
    return applocales.get_locale_string_from_xaml(RESOURCES, key)


selection = revit.get_selection()
if selection.is_empty:
    forms.alert(_t("no_elements"), exitscript=True)

output.set_width(300)

named_elements = sorted(
    ((revit.query.get_name(element) or "", element) for element in selection),
    key=lambda named_element: named_element[0].lower(),
)

if len(selection.element_ids) < SELECT_ALL_LINK_LIMIT:
    output.print_md(output.linkify(selection.element_ids, title=_t("all_elements")))

output.print_table(
    [
        [index, output.linkify(element.Id), escape_for_output(name)]
        for index, (name, element) in enumerate(named_elements, 1)
    ],
    title=_t("table_title"),
    columns=[_t("column_number"), _t("column_id"), _t("column_name")],
)
