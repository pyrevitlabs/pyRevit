# -*- coding: utf-8 -*-
"""Add the elements that the selected tags refer to to the selection."""

from pyrevit import forms, script
from pyrevit import HOST_APP
from pyrevit import revit, DB
from pyrevit.coreutils import applocales

RESOURCES = script.get_bundle_file("resources.xaml")


def _t(key):
    return applocales.get_locale_string_from_xaml(RESOURCES, key)


def tagged_element_ids(tag):
    if isinstance(tag, DB.IndependentTag):
        if HOST_APP.is_newer_than(2022, or_equal=True):
            return list(tag.GetTaggedLocalElementIds())
        return [tag.TaggedLocalElementId]
    if isinstance(tag, DB.Architecture.RoomTag):
        return [tag.TaggedLocalRoomId]
    if isinstance(tag, DB.Mechanical.SpaceTag):
        return [tag.Space.Id] if tag.Space is not None else []
    if isinstance(tag, DB.AreaTag):
        return [tag.Area.Id] if tag.Area is not None else []
    return []


selection = revit.get_selection()

tagged_ids = [
    tagged_id
    for tag in selection
    for tagged_id in tagged_element_ids(tag)
    if tagged_id != DB.ElementId.InvalidElementId
]
if not tagged_ids:
    forms.alert(_t("no_tags"), exitscript=True)

selection.append(tagged_ids)
