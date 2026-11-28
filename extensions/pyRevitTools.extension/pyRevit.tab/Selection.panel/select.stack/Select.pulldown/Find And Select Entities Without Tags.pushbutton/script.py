# -*- coding: utf-8 -*-
"""Select the elements of a category that have no tag in the active view."""

from pyrevit import forms, script
from pyrevit import HOST_APP, revit, DB
from pyrevit.compat import get_elementid_value_func
from pyrevit.coreutils import applocales

RESOURCES = script.get_bundle_file("resources.xaml")
BIC = DB.BuiltInCategory
TAGGABLE_CATEGORIES = [
    (BIC.OST_Rooms, BIC.OST_RoomTags),
    (BIC.OST_Areas, BIC.OST_AreaTags),
    (BIC.OST_MEPSpaces, BIC.OST_MEPSpaceTags),
    (BIC.OST_Doors, BIC.OST_DoorTags),
    (BIC.OST_Windows, BIC.OST_WindowTags),
    (BIC.OST_SpecialityEquipment, BIC.OST_SpecialityEquipmentTags),
    (BIC.OST_MechanicalEquipment, BIC.OST_MechanicalEquipmentTags),
    (BIC.OST_ElectricalEquipment, BIC.OST_ElectricalEquipmentTags),
    (BIC.OST_Walls, BIC.OST_WallTags),
    (BIC.OST_CurtainWallPanels, BIC.OST_CurtainWallPanelTags),
    (BIC.OST_Ceilings, BIC.OST_CeilingTags),
    (BIC.OST_StructuralColumns, BIC.OST_StructuralColumnTags),
    (BIC.OST_Furniture, BIC.OST_FurnitureTags),
    (BIC.OST_FurnitureSystems, BIC.OST_FurnitureSystemTags),
    (BIC.OST_StructuralFraming, BIC.OST_StructuralFramingTags),
    (BIC.OST_StructuralFoundation, BIC.OST_StructuralFoundationTags),
    (BIC.OST_DuctTerminal, BIC.OST_DuctTerminalTags),
    (BIC.OST_CommunicationDevices, BIC.OST_CommunicationDeviceTags),
    (BIC.OST_DataDevices, BIC.OST_DataDeviceTags),
    (BIC.OST_DuctAccessory, BIC.OST_DuctAccessoryTags),
    (BIC.OST_ElectricalFixtures, BIC.OST_ElectricalFixtureTags),
    (BIC.OST_FireAlarmDevices, BIC.OST_FireAlarmDeviceTags),
    (BIC.OST_LightingDevices, BIC.OST_LightingDeviceTags),
    (BIC.OST_LightingFixtures, BIC.OST_LightingFixtureTags),
    (BIC.OST_NurseCallDevices, BIC.OST_NurseCallDeviceTags),
    (BIC.OST_PipeAccessory, BIC.OST_PipeAccessoryTags),
    (BIC.OST_PlumbingFixtures, BIC.OST_PlumbingFixtureTags),
    (BIC.OST_SecurityDevices, BIC.OST_SecurityDeviceTags),
    (BIC.OST_Sprinklers, BIC.OST_SprinklerTags),
    (BIC.OST_TelephoneDevices, BIC.OST_TelephoneDeviceTags),
]
if HOST_APP.is_newer_than(2023, or_equal=True):
    TAGGABLE_CATEGORIES.append(
        (BIC.OST_PlumbingEquipment, BIC.OST_PlumbingEquipmentTags)
    )

get_elementid_value = get_elementid_value_func()


def _t(key):
    return applocales.get_locale_string_from_xaml(RESOURCES, key)


def category_choices():
    choices = {}
    for element_category, tag_category in TAGGABLE_CATEGORIES:
        category = DB.Category.GetCategory(revit.doc, element_category)
        if category:
            choices[category.Name] = (element_category, tag_category)
    return choices


def category_element_ids_in_view(builtin_category, view):
    return list(
        DB.FilteredElementCollector(revit.doc, view.Id)
        .OfCategory(builtin_category)
        .WhereElementIsNotElementType()
        .ToElementIds()
    )


def tagged_element_values(tag):
    if isinstance(tag, DB.Architecture.RoomTag):
        hosts = [tag.Room]
    elif isinstance(tag, DB.AreaTag):
        hosts = [tag.Area]
    elif isinstance(tag, DB.Mechanical.SpaceTag):
        hosts = [tag.Space]
    elif HOST_APP.is_newer_than(2022, or_equal=True):
        return [
            get_elementid_value(host_id) for host_id in tag.GetTaggedLocalElementIds()
        ]
    elif tag.TaggedLocalElementId != DB.ElementId.InvalidElementId:
        return [get_elementid_value(tag.TaggedLocalElementId)]
    else:
        return []
    return [get_elementid_value(host.Id) for host in hosts if host is not None]


def tagged_values_in_view(tag_category, view):
    tag_ids = category_element_ids_in_view(tag_category, view)
    tagged_values = set()
    for tag_id in tag_ids:
        tagged_values.update(tagged_element_values(revit.doc.GetElement(tag_id)))
    return tagged_values


def main():
    choices = category_choices()
    category_name = forms.CommandSwitchWindow.show(
        sorted(choices), message=_t("pick_category")
    )
    if not category_name:
        return
    element_category, tag_category = choices[category_name]
    view = revit.active_view
    element_ids = category_element_ids_in_view(element_category, view)
    if not element_ids:
        forms.alert(_t("no_elements").format(category_name), exitscript=True)
    tagged_values = tagged_values_in_view(tag_category, view)
    untagged_ids = [
        element_id
        for element_id in element_ids
        if get_elementid_value(element_id) not in tagged_values
    ]
    if not untagged_ids:
        forms.alert(_t("all_tagged").format(category_name), exitscript=True)
    revit.get_selection().set_to(untagged_ids)


if __name__ == "__main__":
    main()
