# -*- coding: utf-8 -*-
"""Select the elements of a category that no dimension in the active view references."""

from pyrevit import forms, script
from pyrevit import revit, DB
from pyrevit.compat import get_elementid_value_func
from pyrevit.coreutils import applocales

RESOURCES = script.get_bundle_file("resources.xaml")
DIMENSIONABLE_CATEGORIES = [
    DB.BuiltInCategory.OST_Rooms,
    DB.BuiltInCategory.OST_Areas,
    DB.BuiltInCategory.OST_MEPSpaces,
    DB.BuiltInCategory.OST_Doors,
    DB.BuiltInCategory.OST_Windows,
    DB.BuiltInCategory.OST_SpecialityEquipment,
    DB.BuiltInCategory.OST_MechanicalEquipment,
    DB.BuiltInCategory.OST_ElectricalEquipment,
    DB.BuiltInCategory.OST_Walls,
    DB.BuiltInCategory.OST_CurtainWallPanels,
    DB.BuiltInCategory.OST_Ceilings,
    DB.BuiltInCategory.OST_StructuralColumns,
]

get_elementid_value = get_elementid_value_func()


def _t(key):
    return applocales.get_locale_string_from_xaml(RESOURCES, key)


def category_choices():
    choices = {}
    for builtin_category in DIMENSIONABLE_CATEGORIES:
        category = DB.Category.GetCategory(revit.doc, builtin_category)
        if category:
            choices[category.Name] = builtin_category
    return choices


def element_ids_in_view(builtin_category, view):
    return list(
        DB.FilteredElementCollector(revit.doc, view.Id)
        .OfCategory(builtin_category)
        .WhereElementIsNotElementType()
        .ToElementIds()
    )


def dimensioned_element_values(view):
    dimensions = (
        DB.FilteredElementCollector(revit.doc, view.Id)
        .OfClass(DB.Dimension)
        .WhereElementIsNotElementType()
    )
    return {
        get_elementid_value(reference.ElementId)
        for dimension in dimensions
        for reference in dimension.References
    }


def main():
    choices = category_choices()
    category_name = forms.CommandSwitchWindow.show(
        sorted(choices), message=_t("pick_category")
    )
    if not category_name:
        return
    view = revit.active_view
    element_ids = element_ids_in_view(choices[category_name], view)
    if not element_ids:
        forms.alert(_t("no_elements").format(category_name), exitscript=True)
    dimensioned_values = dimensioned_element_values(view)
    undimensioned_ids = [
        element_id
        for element_id in element_ids
        if get_elementid_value(element_id) not in dimensioned_values
    ]
    if not undimensioned_ids:
        forms.alert(_t("all_dimensioned").format(category_name), exitscript=True)
    revit.get_selection().set_to(undimensioned_ids)


if __name__ == "__main__":
    main()
