"""Keep elements with painted faces in current selection.

If nothing is selected, pick a region to filter painted elements from.
"""
from pyrevit import revit, UI


def _has_painted_faces(el):
    try:
        material_ids = el.GetMaterialIds(True)
        return material_ids.Count > 0
    except Exception:
        return False


class PaintedElementsFilter(UI.Selection.ISelectionFilter):
    def AllowElement(self, element):
        return _has_painted_faces(element)

    def AllowReference(self, reference, point):
        return False


selection = list(revit.get_selection())
if selection:
    filtered = [el.Id for el in selection if _has_painted_faces(el)]
    revit.get_selection().set_to(filtered)
else:
    try:
        elements = revit.pick_rectangle(pick_filter=PaintedElementsFilter())
        revit.get_selection().set_to(elements)
    except Exception:
        pass
