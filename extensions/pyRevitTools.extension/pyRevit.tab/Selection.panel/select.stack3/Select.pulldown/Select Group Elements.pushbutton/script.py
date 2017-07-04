"""Replaces current selection with elements inside the groups."""

from revitutils import doc, uidoc, selection

# noinspection PyUnresolvedReferences
from Autodesk.Revit.DB import ElementId, Group


filtered_elements = []
for el in selection:
    if isinstance(el, Group):
        for subelid in el.GetMemberIds():
            filtered_elements.append(subelid)

selection.set_to(filtered_elements)
