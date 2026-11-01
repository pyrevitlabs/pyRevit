# -*- coding: utf-8 -*-
"""Find and list rooms with identical numbers in the active view."""

from collections import defaultdict

from pyrevit import forms, script
from pyrevit import revit, DB
from pyrevit.coreutils import applocales

from outputtext import escape_for_output

output = script.get_output()

RESOURCES = script.get_bundle_file("resources.xaml")


def _t(key):
    return applocales.get_locale_string_from_xaml(RESOURCES, key)


def can_list_rooms(view):
    """Tell whether the view can be searched for rooms.

    A schedule counts only when it lists rooms, or several categories at once.
    """
    if not DB.FilteredElementCollector.IsViewValidForElementIteration(
        revit.doc, view.Id
    ):
        return False
    if isinstance(view, DB.ViewSchedule):
        category_id = view.Definition.CategoryId
        return category_id in (
            DB.ElementId.InvalidElementId,
            DB.ElementId(DB.BuiltInCategory.OST_Rooms),
        )
    return True


def collect_rooms_by_number():
    rooms_by_number = defaultdict(list)
    rooms = (
        DB.FilteredElementCollector(revit.doc, revit.active_view.Id)
        .OfCategory(DB.BuiltInCategory.OST_Rooms)
        .WhereElementIsNotElementType()
    )
    for room in rooms:
        rooms_by_number[room.Number].append(room)
    return rooms_by_number


def room_row(room):
    room_name = room.get_Parameter(DB.BuiltInParameter.ROOM_NAME).AsString() or ""
    level_name = room.Level.Name if room.Level else _t("no_level")
    return [
        escape_for_output(room_name),
        escape_for_output(level_name),
        output.linkify(room.Id),
    ]


def report(rooms_by_number):
    duplicates = {
        number: rooms for number, rooms in rooms_by_number.items() if len(rooms) > 1
    }
    if not duplicates:
        output.print_md("**{}**".format(_t("no_duplicates")))
        return
    output.print_md("### {}".format(_t("duplicates_found").format(len(duplicates))))
    for number in sorted(duplicates):
        output.print_table(
            table_data=[room_row(room) for room in duplicates[number]],
            title=_t("number_title").format(escape_for_output(number)),
            columns=[_t("column_name"), _t("column_level"), _t("column_show")],
        )


def main():
    if not can_list_rooms(revit.active_view):
        forms.alert(_t("no_rooms_in_view"), exitscript=True)
    report(collect_rooms_by_number())


if __name__ == "__main__":
    main()
