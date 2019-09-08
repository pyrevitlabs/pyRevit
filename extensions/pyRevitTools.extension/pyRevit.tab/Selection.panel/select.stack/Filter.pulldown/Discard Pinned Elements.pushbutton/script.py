"""Discards (not delete) pinned elements from current selection."""

from pyrevit import revit, DB


__context__ = 'Selection'

selection = revit.get_selection()


filtered_elements = []
for el in selection:
    if not el.Pinned:
        filtered_elements.append(el.Id)

selection.set_to(filtered_elements)
