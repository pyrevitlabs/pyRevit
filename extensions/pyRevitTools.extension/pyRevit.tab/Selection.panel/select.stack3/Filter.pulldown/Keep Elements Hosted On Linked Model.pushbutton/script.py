"""Looks into the current selection elements and keeps the ones hosted on a linked model surface."""

from revitutils import doc, uidoc, selection

# noinspection PyUnresolvedReferences
from Autodesk.Revit.DB import ElementId, RevitLinkInstance


__context__ = 'Selection'


filtered_elements = []
for el in selection:
    try:
        host = el.Host
        if isinstance(host, RevitLinkInstance):
            filtered_elements.append(el.Id)
    except:
        continue

selection.set_to(filtered_elements)
