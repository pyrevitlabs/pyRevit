"""Selects elements with no associated tags in current view."""
#pylint: disable=import-error,invalid-name
from collections import namedtuple

from pyrevit import revit, DB, HOST_APP
from pyrevit import forms
from pyrevit.compat import get_value_func
from System.Collections.Generic import List

value_func = get_value_func()

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

    'Furniture': Taggable(
        tag_type=DB.BuiltInCategory.OST_FurnitureTags,
        element_type=DB.BuiltInCategory.OST_Furniture
        ),

    'Furniture Systems': Taggable(
        tag_type=DB.BuiltInCategory.OST_FurnitureSystemTags,
        element_type=DB.BuiltInCategory.OST_FurnitureSystems
        ),
    'Structural framing': Taggable(
        tag_type=DB.BuiltInCategory.OST_StructuralFramingTags,
        element_type=DB.BuiltInCategory.OST_StructuralFraming
        ),
    'Structural foundations': Taggable(
        tag_type=DB.BuiltInCategory.OST_StructuralFoundationTags,
        element_type=DB.BuiltInCategory.OST_StructuralFoundation
        ),
    'Air terminals': Taggable(
        tag_type=DB.BuiltInCategory.OST_DuctTerminalTags,
        element_type=DB.BuiltInCategory.OST_DuctTerminal
        ),
    'Communication devices': Taggable(
        tag_type=DB.BuiltInCategory.OST_CommunicationDeviceTags,
        element_type=DB.BuiltInCategory.OST_CommunicationDevices
        ),
    'Data devices': Taggable(
        tag_type=DB.BuiltInCategory.OST_DataDeviceTags,
        element_type=DB.BuiltInCategory.OST_DataDevices
        ),
    'Duct accessories': Taggable(
        tag_type=DB.BuiltInCategory.OST_DuctAccessoryTags,
        element_type=DB.BuiltInCategory.OST_DuctAccessory
        ),
    'Electrical fixtures': Taggable(
        tag_type=DB.BuiltInCategory.OST_ElectricalFixtureTags,
        element_type=DB.BuiltInCategory.OST_ElectricalFixtures
        ),
    'Fire alarm devices': Taggable(
        tag_type=DB.BuiltInCategory.OST_FireAlarmDeviceTags,
        element_type=DB.BuiltInCategory.OST_FireAlarmDevices
        ),
    'Lighting devices': Taggable(
        tag_type=DB.BuiltInCategory.OST_LightingDeviceTags,
        element_type=DB.BuiltInCategory.OST_LightingDevices
        ),
    'Lighting fixtures': Taggable(
        tag_type=DB.BuiltInCategory.OST_LightingFixtureTags,
        element_type=DB.BuiltInCategory.OST_LightingFixtures
        ),
    'Nurse call devices': Taggable(
        tag_type=DB.BuiltInCategory.OST_NurseCallDeviceTags,
        element_type=DB.BuiltInCategory.OST_NurseCallDevices
        ),
    'Pipe accessories': Taggable(
        tag_type=DB.BuiltInCategory.OST_PipeAccessoryTags,
        element_type=DB.BuiltInCategory.OST_PipeAccessory
        ),
    'Plumbing equipment': Taggable(
        tag_type=DB.BuiltInCategory.OST_PlumbingFixtureTags,
        element_type=DB.BuiltInCategory.OST_PlumbingFixtures
        ),
    'Plumbing fixtures': Taggable(
        tag_type=DB.BuiltInCategory.OST_PlumbingFixtureTags,
        element_type=DB.BuiltInCategory.OST_PlumbingFixtures
        ),
    'Security devices': Taggable(
        tag_type=DB.BuiltInCategory.OST_SecurityDeviceTags,
        element_type=DB.BuiltInCategory.OST_SecurityDevices
        ),
        'Sprinklers': Taggable(
            tag_type=DB.BuiltInCategory.OST_SprinklerTags,
            element_type=DB.BuiltInCategory.OST_Sprinklers
            ),
    'Telephone devices': Taggable(
        tag_type=DB.BuiltInCategory.OST_TelephoneDeviceTags,
        element_type=DB.BuiltInCategory.OST_TelephoneDevices
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
                tagged_rooms.append(value_func(room_tag.Room.Id))

        for room_id in target_elements:
            room = revit.doc.GetElement(room_id)
            if value_func(room.Id) not in tagged_rooms:
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
                tagged_areas.append(value_func(area_tag.Area.Id))

        for area_id in target_elements:
            area = revit.doc.GetElement(area_id)
            if value_func(area.Id) not in tagged_areas:
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
                tagged_spaces.append(value_func(space_tag.Space.Id))

        for space_id in target_elements:
            space = revit.doc.GetElement(space_id)
            if value_func(space.Id) not in tagged_spaces:
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
            elif HOST_APP.is_newer_than(2022, or_equal=True):
                if elt.GetTaggedLocalElementIds() != DB.ElementId.InvalidElementId:
                    tagged_elements.append(List[DB.ElementId](value_func(elt.GetTaggedLocalElementIds())[0]))
            else:
                if elt.TaggedLocalElementId != DB.ElementId.InvalidElementId:
                    tagged_elements.append(value_func(elt.TaggedLocalElementId))
                    
        for elid in target_elements:
            el = revit.doc.GetElement(elid)
            if value_func(el.Id) not in tagged_elements:
                untagged_elements.append(elid)

        if untagged_elements:
            selection.set_to(untagged_elements)
        else:
            forms.alert('All %s have associated tags.'% selected_switch.lower())
