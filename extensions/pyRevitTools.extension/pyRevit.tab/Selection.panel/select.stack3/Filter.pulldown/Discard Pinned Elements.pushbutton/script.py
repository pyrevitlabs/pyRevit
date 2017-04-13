"""Discards (not delete) pinned elements from current selection."""

from revitutils import doc, uidoc, selection

# noinspection PyUnresolvedReferences
from Autodesk.Revit.DB import ElementId, Group


__context__ = 'Selection'


filtered_elements = []
for el in selection:
    if not el.Pinned:
        filtered_elements.append(el.Id)

selection.set_to(filtered_elements)
