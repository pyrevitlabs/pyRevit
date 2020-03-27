"""Selects group instances, which contain selected elements.
By default excludes not-grouped elements from selection.

Shift+Click:
Include not-grouped elements
"""
#pylint: disable=import-error,invalid-name,broad-except
from pyrevit import revit, DB
from pyrevit import forms
from pyrevit import script


__context__ = 'Selection'

logger = script.get_logger()
output = script.get_output()
selection = revit.get_selection()


def get_higher_group(element, level=0):
    logger.debug("Finding higher group id for element: %s" % element.Id)
    if element.GroupId != DB.ElementId.InvalidElementId:
        group = element.Document.GetElement(element.GroupId)
        logger.debug("Element is grouped: %s" % group.Id)
        return get_higher_group(group, level=level + 1)
    else:
        logger.debug("Element is not grouped.")
        if isinstance(element, DB.Group):
            return element


parent_group_ids = set()
ungrouped_element_ids = []

for selected_element in selection:
    higher_group = get_higher_group(selected_element)
    if higher_group:
        logger.debug("Found group: %s", higher_group.Id)
        parent_group_ids.add(higher_group.Id)
    elif __shiftclick__:    #pylint: disable=undefined-variable
        ungrouped_element_ids.append(selected_element.Id)

parent_group_ids.update(ungrouped_element_ids)
selection.set_to(parent_group_ids)
