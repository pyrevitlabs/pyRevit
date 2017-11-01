"""Converts the select text note element into UPPERCASE text."""

from pyrevit import revit


selection = revit.get_selection()

with revit.Transaction('to Upper'):
    for el in selection.elements:
        el.Text = el.Text.upper()
