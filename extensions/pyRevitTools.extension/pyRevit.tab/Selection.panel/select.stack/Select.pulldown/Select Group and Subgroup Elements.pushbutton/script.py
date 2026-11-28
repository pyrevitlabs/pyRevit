# -*- coding: utf-8 -*-
"""Replace the selection with the elements of the selected groups and their subgroups."""

from pyrevit import forms, script
from pyrevit import revit, DB
from pyrevit.coreutils import applocales

RESOURCES = script.get_bundle_file("resources.xaml")


def _t(key):
    return applocales.get_locale_string_from_xaml(RESOURCES, key)


def leaf_member_ids(group):
    for member_id in group.GetMemberIds():
        member = revit.doc.GetElement(member_id)
        if isinstance(member, DB.Group):
            for leaf_id in leaf_member_ids(member):
                yield leaf_id
        else:
            yield member_id


selection = revit.get_selection()

element_ids = [
    leaf_id
    for group in selection.include(DB.Group)
    for leaf_id in leaf_member_ids(group)
]
if not element_ids:
    forms.alert(_t("no_groups"), exitscript=True)

selection.set_to(element_ids)
