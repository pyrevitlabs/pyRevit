# -*- coding: utf-8 -*-
"""Select the elements that pass any of the view filters picked from a list.

The search options (active view or whole project, nested family instances,
reversed result) are stored by the Shift-click configuration in config.py.
"""

from pyrevit import forms, script
from pyrevit import revit, DB
from pyrevit.coreutils import applocales
from pyrevit.framework import to_clr_list

import filter_options

RESOURCES = script.get_bundle_file("resources.xaml")


def _t(key):
    return applocales.get_locale_string_from_xaml(RESOURCES, key)


def pick_element_filters():
    view_filters = list(
        revit.query.get_elements_by_class(DB.ParameterFilterElement, doc=revit.doc)
    )
    if not view_filters:
        forms.alert(_t("no_filters"), exitscript=True)
    picked = forms.SelectFromList.show(
        sorted(view_filters, key=lambda view_filter: view_filter.Name),
        name_attr="Name",
        multiselect=True,
        title=_t("select_title"),
        button_name=_t("select_button"),
    )
    if not picked:
        script.exit()
    element_filters = [view_filter.GetElementFilter() for view_filter in picked]
    element_filters = [
        element_filter for element_filter in element_filters if element_filter
    ]
    if not element_filters:
        forms.alert(_t("no_valid_filters"), exitscript=True)
    return element_filters


def collect_elements(combined_filter, options):
    if options["only_current_view"]:
        forms.check_graphicalview(revit.active_view, exitscript=True)
        collector = DB.FilteredElementCollector(revit.doc, revit.active_view.Id)
    else:
        collector = DB.FilteredElementCollector(revit.doc)
    collector = collector.WhereElementIsNotElementType()
    if options["reverse_filter"]:
        return [
            element
            for element in collector.ToElements()
            if not combined_filter.PassesFilter(element)
        ]
    return collector.WherePasses(combined_filter).ToElements()


def is_nested(element):
    return isinstance(element, DB.FamilyInstance) and element.SuperComponent


def main():
    options = filter_options.load_options(script.get_config())
    element_filters = pick_element_filters()
    combined_filter = DB.LogicalOrFilter(to_clr_list(DB.ElementFilter, element_filters))
    elements = collect_elements(combined_filter, options)
    element_ids = [
        element.Id
        for element in elements
        if not (options["exclude_nested"] and is_nested(element))
    ]
    if not element_ids:
        forms.alert(_t("nothing_found"), exitscript=True)
    revit.get_selection().set_to(element_ids)


if __name__ == "__main__":
    main()
