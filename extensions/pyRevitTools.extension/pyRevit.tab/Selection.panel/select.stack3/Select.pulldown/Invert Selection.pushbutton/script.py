"""Inverts selection in active view.

Shift-Click:
Select group members instead of parent group elements.
"""
#pylint: disable=import-error,invalid-name,broad-except
from pyrevit import revit, DB

__context__ = 'selection'


# get view elements
viewelements = DB.FilteredElementCollector(revit.doc, revit.active_view.Id)\
                 .WhereElementIsNotElementType()\
                 .ToElements()
# remove anything that is a direct DB.Element obj
# these are the weird internal objects that Revit uses like a camera obj
view_element_ids = \
    {x.Id.IntegerValue for x in viewelements if x.GetType() is not DB.Element}

# get current selection
selection = revit.get_selection()
selected_element_ids = {x.Id.IntegerValue for x in selection}

# find elements that are not selected
invert_ids = view_element_ids.difference(selected_element_ids)


# if shiftclick, select all the invert elements
# otherwise do not select elements inside a group
filtered_invert_ids = invert_ids.copy()
if not __shiftclick__: #pylint: disable=undefined-variable
    # collect ids of elements inside a group
    grouped_element_ids = \
        [x.Id.IntegerValue for x in viewelements
         if x.GetType() is not DB.Element
         and x.GroupId != DB.ElementId.InvalidElementId]

    for element_id in invert_ids:
        if element_id in grouped_element_ids:
            filtered_invert_ids.remove(element_id)

# set selection
selection.set_to([DB.ElementId(x) for x in filtered_invert_ids])
