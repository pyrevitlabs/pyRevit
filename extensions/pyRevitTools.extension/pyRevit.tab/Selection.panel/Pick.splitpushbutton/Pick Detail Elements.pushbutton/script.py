"""Activates selection tool that picks only Detail 2D elements."""

from revitutils import uidoc

# noinspection PyUnresolvedReferences
from Autodesk.Revit.DB import Group, ElementId
# noinspection PyUnresolvedReferences
from Autodesk.Revit.UI.Selection import ISelectionFilter
# noinspection PyUnresolvedReferences
from System.Collections.Generic import List


class MassSelectionFilter(ISelectionFilter):
    # standard API override function
    def AllowElement(self, element):
        if element.ViewSpecific:
            if not isinstance(element, Group) and element.GroupId != element.GroupId.InvalidElementId:
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
    sellist = uidoc.Selection.PickElementsByRectangle(sel)

    filteredlist = []
    for el in sellist:
        filteredlist.append(el.Id)

    uidoc.Selection.SetElementIds(List[ElementId](filteredlist))
    uidoc.RefreshActiveView()
except:
    pass
