"""Keep only mirrored elements in current selection

Shift-Click:
Keep only not-Mirrored
"""
#pylint: disable=import-error,invalid-name,broad-except
from pyrevit import revit


__context__ = 'selection'


mirrored_elements = revit.select.select_mirrored(revit.get_selection())
revit.get_selection().set_to(mirrored_elements)
