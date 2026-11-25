# -*- coding: utf-8 -*-
"""Pick and filter helpers shared by the Pick and Filter buttons of the Selection panel.

Those buttons all work the same way: they take elements from the current selection
or from a rectangle the user draws, keep the ones a predicate accepts and make them
the new Revit selection.
"""

from Autodesk.Revit.Exceptions import OperationCanceledException

from pyrevit import script
from pyrevit import revit, UI

logger = script.get_logger()


class PredicateSelectionFilter(UI.Selection.ISelectionFilter):
    """Selection filter that lets the user pick the elements a predicate accepts.

    Args:
        predicate: Callable that takes an element and returns whether it may be
            picked. It runs while the user hovers over elements, so it must be fast
            and must not raise.
    """

    __namespace__ = "pyRevitTools.selectionpick"

    def __init__(self, predicate):
        self._predicate = predicate

    # standard API override function
    def AllowElement(self, element):
        return bool(self._predicate(element))

    # standard API override function
    def AllowReference(self, reference, point):
        return False


def pick_matching(predicate, message=""):
    """Let the user draw a rectangle and return the elements inside it that match.

    Args:
        predicate: Callable that takes an element and returns whether it may be
            picked.
        message: Prompt shown in Revit's status bar while picking.

    Returns:
        The picked elements (possibly none), or None when the user pressed Esc.
    """
    try:
        return revit.pick_rectangle(
            message=message, pick_filter=PredicateSelectionFilter(predicate)
        )
    except OperationCanceledException:
        logger.debug("Rectangle pick cancelled by the user.")
        return None


def select_picked(predicate, message=""):
    """Replace the selection with the matching elements of a rectangle pick.

    Does not apply a new selection when the user cancels the pick; Revit may already
    have cleared the old selection when the pick started. A completed pick that holds
    no matching element clears the selection.
    """
    picked = pick_matching(predicate, message)
    if picked is not None:
        revit.get_selection().set_to(picked)


def keep_matching(predicate, message=""):
    """Narrow the selection to the elements a predicate accepts.

    With nothing selected, the user picks the elements in a rectangle instead, as in
    `select_picked`. A selection that holds only elements of linked models counts as
    nothing selected.
    """
    selection = revit.get_selection()
    selected = list(selection)
    if selected:
        selection.set_to([element.Id for element in selected if predicate(element)])
    else:
        select_picked(predicate, message)
