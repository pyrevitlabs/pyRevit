"""Inverts selection in active view."""

from pyrevit import revit, DB


__context__ = 'selection'


# get view elements
viewelements = DB.FilteredElementCollector(revit.doc, revit.activeview.Id)\
                 .WhereElementIsNotElementType()\
                 .ToElements()

# get current selection
selection = revit.get_selection()

# remove anything that is a direct DB.Element obj
# these are the weird internal objects that Revit uses like a camera obj
filtered_selection = [x for x in viewelements
                      if x not in selection
                      and type(x) is not DB.Element]

# set selection
selection.set_to(filtered_selection)
