"""Keep only editable elements in current selection.

If nothing is selected, pick a region to filter editable elements from.
Works in both workshared and non-workshared documents.
"""
from pyrevit import revit
from pyrevit import DB, UI

doc = revit.doc


def is_editable(el):
    if not doc.IsWorkshared:
        return True
    try:
        status = DB.WorksharingUtils.GetCheckoutStatus(doc, el.Id)
        return status in (
            DB.CheckoutStatus.NotOwned,
            DB.CheckoutStatus.OwnedByCurrentUser,
        )
    except Exception:
        return True


class EditableSelectionFilter(UI.Selection.ISelectionFilter):
    def AllowElement(self, element):
        return is_editable(element)

    def AllowReference(self, reference, point):
        return False


selection = list(revit.get_selection())
if selection:
    editable = [el for el in selection if is_editable(el)]
    revit.get_selection().set_to(editable)
else:
    try:
        elements = revit.pick_rectangle(pick_filter=EditableSelectionFilter())
        revit.get_selection().set_to(elements)
    except Exception:
        pass
