"""Activates selection tool that picks only Detail 2D elements."""

from pyrevit.framework import List
from pyrevit import revit, DB, UI


selection = revit.get_selection()


class MassSelectionFilter(UI.Selection.ISelectionFilter):
    # standard API override function
    def AllowElement(self, element):
        # only allow view-specific (detail) elements
        if element.ViewSpecific:
            # but if it is part of a group, don't select them,
            # unless it is a nested group object
            if not isinstance(element, DB.Group) \
                    and element.GroupId != element.GroupId.InvalidElementId:
                return False
            else:
                return True
        else:
            return False

    # standard API override function
    def AllowReference(self, refer, point):
        return False

try:
    msfilter = MassSelectionFilter()
    selection_list = revit.pick_rectangle(pick_filter=msfilter)

    filtered_list = []
    for el in selection_list:
        filtered_list.append(el.Id)

    selection.set_to(filtered_list)
    revit.uidoc.RefreshActiveView()
except Exception:
    pass
