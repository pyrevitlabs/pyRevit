"""Keep only mirrored elements in current selection.

If nothing is selected, pick a region to filter mirrored elements from.

Shift-Click:
Keep only not-mirrored elements. If nothing is selected, pick a region to
filter non-mirrored elements from.
"""
from pyrevit import revit, EXEC_PARAMS
from pyrevit import UI


class MirroredSelectionFilter(UI.Selection.ISelectionFilter):
    def __init__(self, keep_mirrored=True):
        self._keep_mirrored = keep_mirrored

    def AllowElement(self, element):
        try:
            return element.Mirrored == self._keep_mirrored
        except Exception:
            return False

    def AllowReference(self, reference, point):
        return False


selection = list(revit.get_selection())
if selection:
    filtered = revit.select.select_mirrored(
        selection,
        mirrored=not EXEC_PARAMS.config_mode
    )
    revit.get_selection().set_to(filtered)
else:
    try:
        pick_filter = MirroredSelectionFilter(keep_mirrored=not EXEC_PARAMS.config_mode)
        elements = revit.pick_rectangle(pick_filter=pick_filter)
        revit.get_selection().set_to(elements)
    except Exception:
        pass
