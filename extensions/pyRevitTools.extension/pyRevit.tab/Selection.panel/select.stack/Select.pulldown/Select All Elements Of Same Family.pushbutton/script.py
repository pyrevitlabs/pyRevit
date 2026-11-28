# -*- coding: utf-8 -*-
"""Select all instances of the families of the selected family instances and types."""

from pyrevit import forms, script
from pyrevit import revit, DB
from pyrevit.compat import get_elementid_value_func
from pyrevit.coreutils import applocales

RESOURCES = script.get_bundle_file("resources.xaml")

get_elementid_value = get_elementid_value_func()


def _t(key):
    return applocales.get_locale_string_from_xaml(RESOURCES, key)


def family_of(element):
    if isinstance(element, DB.FamilySymbol):
        return element.Family
    if isinstance(element, DB.FamilyInstance):
        return element.Symbol.Family
    return None


def selected_families():
    families = {}
    for element in revit.get_selection().elements:
        family = family_of(element)
        if family:
            families[get_elementid_value(family.Id)] = family
    return list(families.values())


def instance_ids_of(family):
    instance_ids = []
    for symbol_id in family.GetFamilySymbolIds():
        instance_filter = DB.FamilyInstanceFilter(revit.doc, symbol_id)
        instance_ids.extend(
            DB.FilteredElementCollector(revit.doc)
            .WherePasses(instance_filter)
            .ToElementIds()
        )
    return instance_ids


def main():
    families = selected_families()
    if not families:
        forms.alert(_t("no_family_instances"), exitscript=True)
    instance_ids = []
    for family in families:
        instance_ids.extend(instance_ids_of(family))
    if not instance_ids:
        forms.alert(_t("no_instances"), exitscript=True)
    revit.get_selection().set_to(instance_ids)


if __name__ == "__main__":
    main()
