"""Discards (not delete) grouped elements from the current selection."""

from pyrevit import revit, DB


__context__ = 'Selection'

selection = revit.get_selection()


filtered_elements = []
for el in selection:
    if el.GroupId == DB.ElementId.InvalidElementId \
            and not isinstance(el, DB.Group):
        filtered_elements.append(el.Id)

selection.set_to(filtered_elements)
