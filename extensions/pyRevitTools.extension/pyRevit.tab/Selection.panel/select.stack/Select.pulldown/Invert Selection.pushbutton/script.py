# -*- coding: utf-8 -*-
"""Select what is not selected in the active view."""

# pylint: disable=import-error,invalid-name,broad-except
from pyrevit import revit, DB, EXEC_PARAMS
from pyrevit.compat import get_elementid_value_func

get_elementid_value = get_elementid_value_func()


def is_selectable(element):
    # remove anything that is a direct DB.Element obj
    # these are the weird internal objects that Revit uses like a camera obj
    return element.GetType() is not DB.Element


def is_group_member(element):
    return element.GroupId != DB.ElementId.InvalidElementId


selection = revit.get_selection()
selected_values = {
    get_elementid_value(element_id) for element_id in selection.element_ids
}

view_elements = [
    element
    for element in DB.FilteredElementCollector(revit.doc, revit.active_view.Id)
    .WhereElementIsNotElementType()
    .ToElements()
    if is_selectable(element)
]

# if shiftclick, select all the invert elements
# otherwise do not select elements inside a group
inverted_ids = [
    element.Id
    for element in view_elements
    if get_elementid_value(element.Id) not in selected_values
    and (EXEC_PARAMS.config_mode or not is_group_member(element))
]

selection.set_to(inverted_ids)
