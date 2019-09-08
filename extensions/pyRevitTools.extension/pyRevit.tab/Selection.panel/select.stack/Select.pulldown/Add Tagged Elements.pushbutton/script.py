from pyrevit import revit, DB, UI
from pyrevit import forms


__context__ = 'selection'
__doc__ = 'Select a series of tags and this tool will add their associated '\
          'elements to selection. This is especially useful for isolating '\
          'elements and their tags.'

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
