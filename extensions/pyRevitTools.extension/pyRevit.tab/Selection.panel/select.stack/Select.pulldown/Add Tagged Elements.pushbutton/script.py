from pyrevit import revit, DB, UI
from pyrevit import forms


selection = revit.get_selection()


tagged_elements = []

for el in selection:
    if isinstance(el, DB.IndependentTag):
        tagged_elements.append(el.TaggedLocalElementId)
    elif isinstance(el, DB.Architecture.RoomTag):
        tagged_elements.append(el.TaggedLocalRoomId)
    elif isinstance(el, DB.Mechanical.SpaceTag):
        tagged_elements.append(el.Space.Id)
    elif isinstance(el, DB.AreaTag):
        tagged_elements.append(el.Area.Id)

if len(tagged_elements) > 0:
    selection.append(tagged_elements)
else:
    forms.alert('Please select at least one element tag.')
