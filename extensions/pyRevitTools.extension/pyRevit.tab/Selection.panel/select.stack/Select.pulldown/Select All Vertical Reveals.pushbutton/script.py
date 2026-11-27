# -*- coding: utf-8 -*-
"""Select all vertical wall reveals, or all horizontal ones in config mode."""

# pylint: disable=import-error,invalid-name
from pyrevit import forms, script
from pyrevit import revit, DB, EXEC_PARAMS
from pyrevit.coreutils import applocales

RESOURCES = script.get_bundle_file("resources.xaml")


def _t(key):
    return applocales.get_locale_string_from_xaml(RESOURCES, key)


select_vertical = not EXEC_PARAMS.config_mode

reveals = (
    DB.FilteredElementCollector(revit.doc)
    .OfCategory(DB.BuiltInCategory.OST_Reveals)
    .WhereElementIsNotElementType()
    .ToElements()
)
reveal_ids = [
    reveal.Id
    for reveal in reveals
    if reveal.GetWallSweepInfo().IsVertical == select_vertical
]
if not reveal_ids:
    no_reveals_key = (
        "no_vertical_reveals" if select_vertical else "no_horizontal_reveals"
    )
    forms.alert(_t(no_reveals_key), exitscript=True)

revit.get_selection().set_to(reveal_ids)
