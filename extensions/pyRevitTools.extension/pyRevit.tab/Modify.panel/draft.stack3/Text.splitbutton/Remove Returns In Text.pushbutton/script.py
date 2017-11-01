"""Removes all newlines in the selected text note element."""


from pyrevit import revit


selection = revit.get_selection()

with revit.Transaction('Merge Single-Line Text'):
    for el in selection.elements:
        el.Text = str(el.Text).replace('\r', ' ')
