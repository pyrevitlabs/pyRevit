"""keeps elements with painted faces in current selection and filters everything else out."""

from pyrevit import revit, DB


__context__ = 'Selection'

selection = revit.get_selection()


filtered_elements = []
for el in selection:
    if len(list(el.GetMaterialIds(True))) > 0:
        filtered_elements.append(el.Id)

selection.set_to(filtered_elements)
