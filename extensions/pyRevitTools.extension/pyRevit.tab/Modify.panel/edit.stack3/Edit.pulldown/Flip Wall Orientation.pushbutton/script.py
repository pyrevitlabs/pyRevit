"""Flips wall orientation on the selected walls."""

from pyrevit import revit, DB

selection = revit.get_selection()

with revit.Transaction('Flip Selected Walls'):
    for el in selection:
        if isinstance(el, DB.Wall):
            el.flipHand()
