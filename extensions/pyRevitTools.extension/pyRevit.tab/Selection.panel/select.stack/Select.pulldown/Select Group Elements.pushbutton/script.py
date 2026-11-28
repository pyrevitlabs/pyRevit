# -*- coding: utf-8 -*-
"""Replace the selection with the members of the selected groups."""

from pyrevit import forms, script
from pyrevit import revit, DB
from pyrevit.coreutils import applocales

RESOURCES = script.get_bundle_file("resources.xaml")


def _t(key):
    return applocales.get_locale_string_from_xaml(RESOURCES, key)


selection = revit.get_selection()

member_ids = [
    member_id
    for group in selection.include(DB.Group)
    for member_id in group.GetMemberIds()
]
if not member_ids:
    forms.alert(_t("no_groups"), exitscript=True)

selection.set_to(member_ids)
