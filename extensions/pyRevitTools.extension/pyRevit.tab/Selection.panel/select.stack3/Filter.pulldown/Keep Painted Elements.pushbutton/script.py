"""keeps elements with painted faces in current selection and filters everything else out."""

from revitutils import doc, uidoc, selection

# noinspection PyUnresolvedReferences
from Autodesk.Revit.DB import ElementId, Group


__context__ = 'Selection'


filtered_elements = []
for el in selection:
    if len(list(el.GetMaterialIds(True))) > 0:
        filtered_elements.append(el.Id)

selection.set_to(filtered_elements)
