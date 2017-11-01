"""Converts the select text note element into lowercase text."""

from pyrevit import revit


selection = revit.get_selection()

with revit.Transaction('to Lower'):
    for el in selection.elements:
        el.Text = el.Text.lower()
