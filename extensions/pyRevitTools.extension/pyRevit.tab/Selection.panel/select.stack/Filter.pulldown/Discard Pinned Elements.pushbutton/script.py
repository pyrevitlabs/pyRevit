"""Discard pinned elements from current selection.

If nothing is selected, pick a region to filter non-pinned elements from.
"""
from pyrevit import revit, UI


class NonPinnedSelectionFilter(UI.Selection.ISelectionFilter):
    def AllowElement(self, element):
        return not element.Pinned

    def AllowReference(self, reference, point):
        return False


selection = list(revit.get_selection())
if selection:
    filtered = [el.Id for el in selection if not el.Pinned]
    revit.get_selection().set_to(filtered)
else:
    try:
        elements = revit.pick_rectangle(pick_filter=NonPinnedSelectionFilter())
        revit.get_selection().set_to(elements)
    except Exception:
        pass
