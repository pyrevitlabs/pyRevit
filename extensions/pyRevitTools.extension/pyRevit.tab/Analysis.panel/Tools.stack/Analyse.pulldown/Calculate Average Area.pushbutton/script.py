# -*- coding: utf-8 -*-
"""Find all rooms, areas or spaces named like the selected ones and report their average area."""

from pyrevit import forms, script
from pyrevit import revit, DB
from pyrevit.coreutils import applocales, escape_for_html
from pyrevit.revit import query

output = script.get_output()

RESOURCES = script.get_bundle_file("resources.xaml")

SQUARE_FEET_PER_ACRE = 43560.0
SQUARE_FEET_PER_HECTARE = 107639.0

SPATIAL_KINDS = (
    (DB.Area, DB.BuiltInCategory.OST_Areas, "kind_area"),
    (DB.Architecture.Room, DB.BuiltInCategory.OST_Rooms, "kind_room"),
    (DB.Mechanical.Space, DB.BuiltInCategory.OST_MEPSpaces, "kind_space"),
)


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


def read_text(element, builtin_parameter):
    return element.Parameter[builtin_parameter].AsString() or ""


def read_level_name(element):
    return element.Parameter[DB.BuiltInParameter.ROOM_LEVEL_ID].AsValueString() or ""


def read_area(element):
    return element.Parameter[DB.BuiltInParameter.ROOM_AREA].AsDouble()


def describe(element):
    return [
        output.linkify(element.Id),
        escape_for_output(read_text(element, DB.BuiltInParameter.ROOM_NUMBER)),
        escape_for_output(read_text(element, DB.BuiltInParameter.ROOM_NAME)),
        escape_for_output(read_level_name(element)),
    ]


def find_kind(element):
    for element_class, category, kind_key in SPATIAL_KINDS:
        if isinstance(element, element_class):
            return element_class, category, kind_key
    return None


def report_group(kind_label, name, placed, unplaced):
    output.print_md("### {}: {}".format(kind_label, escape_for_output(name)))
    if placed:
        output.print_table(
            table_data=[
                describe(item) + [revit.units.format_area(read_area(item))]
                for item in placed
            ],
            columns=[
                _t("column_element"),
                _t("column_number"),
                _t("column_name"),
                _t("column_level"),
                _t("column_area"),
            ],
        )
    if unplaced:
        output.print_table(
            table_data=[describe(item) for item in unplaced],
            title=_t("skipped_title"),
            columns=[
                _t("column_element"),
                _t("column_number"),
                _t("column_name"),
                _t("column_level"),
            ],
        )
    output.print_md("**{}**".format(_t("total_found").format(len(placed))))
    if not placed:
        return
    average = sum(read_area(item) for item in placed) / len(placed)
    output.print_md(
        "**{}**  \n{}".format(
            _t("average_area").format(revit.units.format_area(average)),
            _t("average_area_alt").format(
                average / SQUARE_FEET_PER_ACRE, average / SQUARE_FEET_PER_HECTARE
            ),
        )
    )


def main():
    reported = set()
    elements_by_category = {}
    for selected in revit.get_selection().elements:
        kind = find_kind(selected)
        if not kind:
            continue
        element_class, category, kind_key = kind
        name = read_text(selected, DB.BuiltInParameter.ROOM_NAME)
        if (element_class, name) in reported:
            continue
        reported.add((element_class, name))
        if category not in elements_by_category:
            elements_by_category[category] = query.get_elements_by_categories(
                [category]
            )
        siblings = [
            item
            for item in elements_by_category[category]
            if read_text(item, DB.BuiltInParameter.ROOM_NAME) == name
        ]
        report_group(
            _t(kind_key),
            name,
            [item for item in siblings if query.is_placed(item)],
            [item for item in siblings if not query.is_placed(item)],
        )
    if not reported:
        forms.alert(_t("select_spatial_element"), exitscript=True)


main()
