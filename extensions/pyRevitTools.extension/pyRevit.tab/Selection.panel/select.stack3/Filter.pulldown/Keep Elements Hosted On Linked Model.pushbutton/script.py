"""Looks into the current selection elements and keeps the ones hosted on a linked model surface."""

from pyrevit import revit, DB


__context__ = 'Selection'

selection = revit.get_selection()


filtered_elements = []
for el in selection:
    try:
        host = el.Host
        if isinstance(host, DB.RevitLinkInstance):
            filtered_elements.append(el.Id)
    except:
        continue

selection.set_to(filtered_elements)
