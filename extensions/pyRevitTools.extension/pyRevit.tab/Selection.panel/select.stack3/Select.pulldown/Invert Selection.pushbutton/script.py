"""Inverts selection in active view.

Shift-Click: select groups instead of group members"""

from pyrevit import revit, DB


__context__ = 'selection'


# get view elements
viewelements = DB.FilteredElementCollector(revit.doc, revit.activeview.Id)\
                 .WhereElementIsNotElementType()\
                 .ToElements()

# get current selection
selection = revit.get_selection()

# get selected groups
if __shiftclick__:
    selected_group_ids = [el.Id for el in selection if isinstance(el, DB.Group)]

# remove anything that is a direct DB.Element obj
# these are the weird internal objects that Revit uses like a camera obj
filtered_selection = [x for x in viewelements
                      if x not in selection
                      and type(x) is not DB.Element]                  

# exclude grouped elements
if __shiftclick__:
    filtered_selection = [x for x in filtered_selection
                          if x.GroupId.IntegerValue == -1]

# set selection
selection.set_to(filtered_selection)
