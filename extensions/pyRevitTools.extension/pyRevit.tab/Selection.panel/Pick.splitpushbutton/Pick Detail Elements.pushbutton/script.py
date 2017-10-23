"""Activates selection tool that picks only Detail 2D elements."""

from pyrevit.framework import List
from pyrevit import revit, DB, UI


class MassSelectionFilter(UI.Selection.ISelectionFilter):
    # standard API override function
    def AllowElement(self, element):
        if element.ViewSpecific:
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
    sel = MassSelectionFilter()
    selection_list = revit.uidoc.Selection.PickElementsByRectangle(sel)

    filtered_list = []
    for el in selection_list:
        filtered_list.append(el.Id)

    revit.uidoc.Selection.SetElementIds(List[DB.ElementId](filtered_list))
    revit.uidoc.RefreshActiveView()
except Exception:
    pass
