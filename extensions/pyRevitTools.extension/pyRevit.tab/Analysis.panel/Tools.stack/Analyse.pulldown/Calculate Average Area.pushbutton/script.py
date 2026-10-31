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


processed_items = {DB.Area: [], DB.Architecture.Room: [], DB.Mechanical.Space: []}


selection = revit.get_selection()


def calc_and_print(items, item_type, type_name, match_name):
    item_total_area = 0.0
    item_count = 0
    if match_name not in processed_items[item_type]:
        print("{} TYPE IS: {}".format(type_name, match_name))
        for item in items:
            item_name = item.get_Parameter(DB.BuiltInParameter.ROOM_NAME).AsString()
            item_number = item.get_Parameter(DB.BuiltInParameter.ROOM_NUMBER).AsString()
            item_level = item.get_Parameter(
                DB.BuiltInParameter.ROOM_LEVEL_ID
            ).AsValueString()
            if revit.query.is_placed(item):
                if match_name == item_name:
                    area_value = item.get_Parameter(
                        DB.BuiltInParameter.ROOM_AREA
                    ).AsDouble()
                    print(
                        '{} {} #{} "{}" @ "{}" = {}'.format(
                            output.linkify(item.Id),
                            type_name.title(),
                            item_number,
                            item_name,
                            item_level,
                            revit.units.format_area(area_value),
                        )
                    )
                    item_total_area += area_value
                    item_count += 1
            else:
                print(
                    ':cross_mark: SKIPPED "NOT PLACED" {} {} #{} "{}" @ "{}"'.format(
                        output.linkify(item.Id),
                        type_name.title(),
                        item_number,
                        item_name,
                        item_level,
                    )
                )
        print("TOTAL OF {} {}S WERE FOUND.".format(item_count, type_name))
        processed_items[item_type].append(match_name)
    return item_total_area, item_count


for el in selection.elements:
    count = 0
    total = 0.0
    if isinstance(el, DB.Area):
        target_name = el.get_Parameter(DB.BuiltInParameter.ROOM_NAME).AsString()
        area_total, area_count = calc_and_print(areas, DB.Area, "AREA", target_name)
        count += area_count
        total += area_total
    elif isinstance(el, DB.Architecture.Room):
        target_name = el.get_Parameter(DB.BuiltInParameter.ROOM_NAME).AsString()
        area_total, area_count = calc_and_print(
            rooms, DB.Architecture.Room, "ROOM", target_name
        )
        count += area_count
        total += area_total
    elif isinstance(el, DB.Mechanical.Space):
        target_name = el.get_Parameter(DB.BuiltInParameter.ROOM_NAME).AsString()
        area_total, area_count = calc_and_print(
            spaces, DB.Mechanical.Space, "SPACE", target_name
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
