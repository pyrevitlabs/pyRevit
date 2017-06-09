from revitutils import doc, uidoc, selection

# noinspection PyUnresolvedReferences
from Autodesk.Revit.DB import ElementId, IndependentTag, AreaTag
# noinspection PyUnresolvedReferences
from Autodesk.Revit.DB.Architecture import RoomTag
# noinspection PyUnresolvedReferences
from Autodesk.Revit.DB.Mechanical import SpaceTag
# noinspection PyUnresolvedReferences
from Autodesk.Revit.UI import TaskDialog


__doc__ = 'Select a series of tags and this tool will add their associated elements to selection. ' \
          'This is especially useful for isolating elements and their tags.'


tagged_elements = []

for el in selection:
    if isinstance(el, IndependentTag):
        tagged_elements.append(el.TaggedLocalElementId)
    elif isinstance(el, RoomTag):
        tagged_elements.append(el.TaggedLocalRoomId)
    elif isinstance(el, SpaceTag):
        tagged_elements.append(el.Space.Id)
    elif isinstance(el, AreaTag):
        tagged_elements.append(el.Area.Id)

if len(tagged_elements) > 0:
    selection.append(tagged_elements)
else:
    TaskDialog.Show('pyrevit', 'Please select at least one element tag.')
