# -*- coding: utf-8 -*-
"""Replace the selection with the member walls of the selected stacked walls."""

from pyrevit import forms, script
from pyrevit import revit, DB
from pyrevit.coreutils import applocales

RESOURCES = script.get_bundle_file("resources.xaml")


def _t(key):
    return applocales.get_locale_string_from_xaml(RESOURCES, key)


def sub_wall_ids(wall):
    if wall.IsStackedWall:
        return list(wall.GetStackedWallMemberIds())
    return [wall.Id]


selection = revit.get_selection()

wall_ids = [
    wall_id for wall in selection.include(DB.Wall) for wall_id in sub_wall_ids(wall)
]
if not wall_ids:
    forms.alert(_t("no_stacked_walls"), exitscript=True)

selection.set_to(wall_ids)
