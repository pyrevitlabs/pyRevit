"""Flips hand on the selected doors."""

from pyrevit import revit

selection = revit.get_selection()

with revit.Transaction('Flip Hand Selected Doors'):
    for el in selection:
        if el.Category.Name == 'Doors':
            el.flipHand()
