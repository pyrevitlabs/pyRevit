from pyrevit import revit, DB, UI, HOST_APP
from pyrevit import forms
#  import List
from System.Collections.Generic import List


selection = revit.get_selection()


tagged_elements = []

for el in selection:
    if HOST_APP.is_newer_than(2022, or_equal=True):
        if isinstance(el, DB.IndependentTag):
            tagged_elements.append(List[DB.ElementId](el.GetTaggedLocalElementIds())[0])
        elif isinstance(el, DB.Architecture.RoomTag):
            tagged_elements.append(el.TaggedLocalRoomId)
        elif isinstance(el, DB.Mechanical.SpaceTag):
            tagged_elements.append(el.Space.Id)
        elif isinstance(el, DB.AreaTag):
            tagged_elements.append(el.Area.Id)
    else:

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
