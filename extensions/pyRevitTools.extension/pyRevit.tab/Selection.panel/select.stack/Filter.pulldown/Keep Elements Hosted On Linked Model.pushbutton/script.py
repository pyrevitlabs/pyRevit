"""Keep elements hosted on a linked model surface in current selection.

If nothing is selected, pick a region to filter linked-hosted elements from.
"""
from pyrevit import revit, DB, UI
from pyrevit import script


logger = script.get_logger()


def _is_hosted_on_link(el):
    try:
        return isinstance(el.Host, DB.RevitLinkInstance)
    except Exception as err:
        logger.debug("{} | {}".format(el.Id, err))
        return False


class LinkedModelHostedFilter(UI.Selection.ISelectionFilter):
    def AllowElement(self, element):
        return _is_hosted_on_link(element)

    def AllowReference(self, reference, point):
        return False


selection = list(revit.get_selection())
if selection:
    filtered = [el.Id for el in selection if _is_hosted_on_link(el)]
    revit.get_selection().set_to(filtered)
else:
    try:
        elements = revit.pick_rectangle(pick_filter=LinkedModelHostedFilter())
        revit.get_selection().set_to(elements)
    except Exception:
        pass
