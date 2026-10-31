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

output = script.get_output()

RESOURCES = script.get_bundle_file("resources.xaml")
LINK_URL_LIMIT = 2000
OPENING_FILTER_NAME = "0_ShaftOpenings"
OPENING_CATEGORIES = [
    DB.BuiltInCategory.OST_FloorOpening,
    DB.BuiltInCategory.OST_SWallRectOpening,
    DB.BuiltInCategory.OST_ShaftOpening,
    DB.BuiltInCategory.OST_RoofOpening,
]


def _t(key):
    return applocales.get_locale_string_from_xaml(RESOURCES, key)


def escape_for_output(text):
    """Make model text render literally in print_table cells and print_md headings.

    print_table splits cells on pipes and renders Markdown, so pipes, emphasis and
    link characters are encoded as entities. Ampersands are encoded so names such
    as "&copy;" are not read as entities, and line breaks become spaces so a name
    stays on one table row.
    """
    escaped = escape_for_html(" ".join(text.splitlines()).replace("&", "&#38;"))
    for character in "|*_`[":
        escaped = escaped.replace(character, "&#{};".format(ord(character)))
    return escaped


def collect_openings():
    """Collect the openings of ``OPENING_CATEGORIES``.

    Note:
        Filters by ``BuiltInCategory`` directly: these categories are missing from
        ``doc.Settings.Categories``, so ``query.get_elements_by_categories`` skips
        most of them.
    """
    return (
        DB.FilteredElementCollector(revit.doc)
        .WherePasses(
            DB.ElementMulticategoryFilter(List[DB.BuiltInCategory](OPENING_CATEGORIES))
        )
        .WhereElementIsNotElementType()
        .ToElements()
    )


def sync_opening_filter(openings):
    """Create the selection filter for the openings, or reset the existing one to them.

    Args:
        openings: The openings of the categories in ``OPENING_CATEGORIES``, the
            same set the report lists.

    Returns:
        bool: True if the filter was created, False if an existing one was updated.
    """
    opening_ids = List[DB.ElementId](opening.Id for opening in openings)
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
        opening_filter.SetElementIds(opening_ids)
    return created


def split_ids_for_links(element_ids):
    """Split element ids into groups that each fit in one ``output.linkify`` link.

    Note:
        ``output.linkify`` refuses links whose ``element[]=<id>&...`` query reaches
        ``LINK_URL_LIMIT`` characters, so a single link cannot select every opening
        of a large project.
    """
    get_elementid_value = get_elementid_value_func()
    groups = []
    group = []
    group_length = 0
    for element_id in element_ids:
        query_length = len("element[]={}&".format(get_elementid_value(element_id)))
        if group and group_length + query_length >= LINK_URL_LIMIT:
            groups.append(group)
            group = []
            group_length = 0
        group.append(element_id)
        group_length += query_length
    if group:
        groups.append(group)
    return groups


def select_all_links(openings):
    groups = split_ids_for_links([opening.Id for opening in openings])
    if len(groups) == 1:
        return output.linkify(groups[0], title=_t("select_all"))
    return " ".join(
        output.linkify(group, title=_t("select_part").format(number, len(groups)))
        for number, group in enumerate(groups, 1)
    )


def report(openings):
    output.print_md("#### {}".format(_t("openings_in_project").format(len(openings))))
    if not openings:
        return
    output.print_md(select_all_links(openings))
    get_elementid_value = get_elementid_value_func()
    output.print_table(
        table_data=[
            [
                escape_for_output(opening.Name),
                get_elementid_value(opening.Id),
                output.linkify(opening.Id),
            ]
            for opening in openings
        ],
        title=_t("table_title"),
        columns=[_t("column_name"), _t("column_id"), _t("column_show")],
    )


started = time.time()
openings = collect_openings()
filter_message = "created_filter" if sync_opening_filter(openings) else "updated_filter"
output.print_md(_t(filter_message).format(OPENING_FILTER_NAME))
report(openings)
output.print_md("---")
output.print_md("#### {}".format(_t("finished_in").format(time.time() - started)))
