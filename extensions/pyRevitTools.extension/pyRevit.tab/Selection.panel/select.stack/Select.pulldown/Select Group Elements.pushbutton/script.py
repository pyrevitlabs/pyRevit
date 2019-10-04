"""Replaces current selection with elements inside the groups."""

from pyrevit import revit, DB


__context__ = 'selection'


selection = revit.get_selection()


filtered_elements = []
for el in selection:
    if isinstance(el, DB.Group):
        for subelid in el.GetMemberIds():
            filtered_elements.append(subelid)

selection.set_to(filtered_elements)
