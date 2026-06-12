"""Discard grouped elements from current selection.

If nothing is selected, pick a region to filter non-grouped elements from.
"""
from pyrevit import revit, DB, UI


def _is_non_grouped(el):
    return el.GroupId == DB.ElementId.InvalidElementId and not isinstance(el, DB.Group)


class NonGroupedSelectionFilter(UI.Selection.ISelectionFilter):
    def AllowElement(self, element):
        return _is_non_grouped(element)

    def AllowReference(self, reference, point):
        return False


selection = list(revit.get_selection())
if selection:
    filtered = [el.Id for el in selection if _is_non_grouped(el)]
    revit.get_selection().set_to(filtered)
else:
    try:
        elements = revit.pick_rectangle(pick_filter=NonGroupedSelectionFilter())
        revit.get_selection().set_to(elements)
    except Exception:
        pass
