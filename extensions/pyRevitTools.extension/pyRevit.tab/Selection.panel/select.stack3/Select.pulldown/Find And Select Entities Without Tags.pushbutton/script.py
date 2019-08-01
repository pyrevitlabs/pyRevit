"""Selects elements with no associated tags in current view."""
#pylint: disable=import-error,invalid-name
from collections import namedtuple

from pyrevit import revit, DB
from pyrevit import forms


Taggable = namedtuple('Taggable', ['tag_type', 'element_type'])


# make sure active view is not a sheet
curview = revit.active_view
if isinstance(curview, DB.ViewSheet):
    forms.alert("You're on a Sheet. Activate a model view please.",
                exitscript=True)


options = {
    'Rooms': Taggable(
        tag_type=DB.BuiltInCategory.OST_RoomTags,
        element_type=DB.BuiltInCategory.OST_Rooms
        ),

    'Areas': Taggable(
        tag_type=DB.BuiltInCategory.OST_AreaTags,
        element_type=DB.BuiltInCategory.OST_Areas
        ),

    'Spaces': Taggable(
        tag_type=DB.BuiltInCategory.OST_MEPSpaceTags,
        element_type=DB.BuiltInCategory.OST_MEPSpaces
        ),

    'Doors': Taggable(
        tag_type=DB.BuiltInCategory.OST_DoorTags,
        element_type=DB.BuiltInCategory.OST_Doors
        ),

    'Windows': Taggable(
        tag_type=DB.BuiltInCategory.OST_WindowTags,
        element_type=DB.BuiltInCategory.OST_Windows
        ),

    'Speciality Equipment': Taggable(
        tag_type=DB.BuiltInCategory.OST_SpecialityEquipmentTags,
        element_type=DB.BuiltInCategory.OST_SpecialityEquipment
        ),

    'Mechanical Equipment': Taggable(
        tag_type=DB.BuiltInCategory.OST_MechanicalEquipmentTags,
        element_type=DB.BuiltInCategory.OST_MechanicalEquipment
        ),

    'Electrical Equipment': Taggable(
        tag_type=DB.BuiltInCategory.OST_ElectricalEquipmentTags,
        element_type=DB.BuiltInCategory.OST_ElectricalEquipment
        ),

    'Walls': Taggable(
        tag_type=DB.BuiltInCategory.OST_WallTags,
        element_type=DB.BuiltInCategory.OST_Walls
        ),

    'Curtain Walls': Taggable(
        tag_type=DB.BuiltInCategory.OST_CurtainWallPanelTags,
        element_type=DB.BuiltInCategory.OST_CurtainWallPanels
        ),

    'Ceilings': Taggable(
        tag_type=DB.BuiltInCategory.OST_CeilingTags,
        element_type=DB.BuiltInCategory.OST_Ceilings
        ),

    'Columns': Taggable(
        tag_type=DB.BuiltInCategory.OST_StructuralColumnTags,
        element_type=DB.BuiltInCategory.OST_StructuralColumns
        ),
}

selected_switch = \
    forms.CommandSwitchWindow.show(sorted(options.keys()),
                                   message='Find untagged elements of type:')


if selected_switch:
    target = options[selected_switch]
    selection = revit.get_selection()

    # collect target elements and tags in view
    target_tags = DB.FilteredElementCollector(revit.doc, curview.Id)\
                .OfCategory(target.tag_type)\
                .WhereElementIsNotElementType()\
                .ToElementIds()

    target_elements = DB.FilteredElementCollector(revit.doc, curview.Id)\
            .OfCategory(target.element_type)\
            .WhereElementIsNotElementType()\
            .ToElementIds()

    if selected_switch == 'Rooms':
        tagged_rooms = []
        untagged_rooms = []
        for room_tag_id in target_tags:
            room_tag = revit.doc.GetElement(room_tag_id)
            if room_tag.Room is not None:
                tagged_rooms.append(room_tag.Room.Id.IntegerValue)

        for room_id in target_elements:
            room = revit.doc.GetElement(room_id)
            if room.Id.IntegerValue not in tagged_rooms:
                untagged_rooms.append(room_id)

        if untagged_rooms:
            selection.set_to(untagged_rooms)
        else:
            forms.alert('All rooms have associated tags.')

    elif selected_switch == 'Areas':
        tagged_areas = []
        untagged_areas = []
        for area_tag_id in target_tags:
            area_tag = revit.doc.GetElement(area_tag_id)
            if area_tag.Area is not None:
                tagged_areas.append(area_tag.Area.Id.IntegerValue)

        for area_id in target_elements:
            area = revit.doc.GetElement(area_id)
            if area.Id.IntegerValue not in tagged_areas:
                untagged_areas.append(area_id)

        if untagged_areas:
            selection.set_to(untagged_areas)
        else:
            forms.alert('All areas have associated tags.')

    elif selected_switch == 'Spaces':
        tagged_spaces = []
        untagged_spaces = []
        for space_tag_id in target_tags:
            space_tag = revit.doc.GetElement(space_tag_id)
            if space_tag.Space is not None:
                tagged_spaces.append(space_tag.Space.Id.IntegerValue)

        for space_id in target_elements:
            space = revit.doc.GetElement(space_id)
            if space.Id.IntegerValue not in tagged_spaces:
                untagged_spaces.append(space_id)

        if untagged_spaces:
            selection.set_to(untagged_spaces)
        else:
            forms.alert('All spaces have associated tags.')

    else:
        tagged_elements = []
        untagged_elements = []
        for eltid in target_tags:
            elt = revit.doc.GetElement(eltid)
            if elt.TaggedLocalElementId != DB.ElementId.InvalidElementId:
                tagged_elements.append(elt.TaggedLocalElementId.IntegerValue)

        for elid in target_elements:
            el = revit.doc.GetElement(elid)
            if el.Id.IntegerValue not in tagged_elements:
                untagged_elements.append(elid)

        if untagged_elements:
            selection.set_to(untagged_elements)
        else:
            forms.alert('All %s have associated tags.'% selected_switch.lower())
