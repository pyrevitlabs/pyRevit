# -*- coding: utf-8 -*-
"""Select all elements that have the type of a selected element.

Lines match by line style. Shift-click also lists the selected elements in the
output window, grouped by the view that owns them when they are view-specific.
"""

from pyrevit import forms, script
from pyrevit import EXEC_PARAMS, revit, DB
from pyrevit.compat import get_elementid_value_func
from pyrevit.coreutils import applocales, escape_for_output

output = script.get_output()

RESOURCES = script.get_bundle_file("resources.xaml")

get_elementid_value = get_elementid_value_func()


def _t(key):
    return applocales.get_locale_string_from_xaml(RESOURCES, key)


def type_value(element):
    if isinstance(element, DB.CurveElement):
        return get_elementid_value(element.LineStyle.Id)
    return get_elementid_value(element.GetTypeId())


def collector_key(element):
    if isinstance(element, DB.Dimension):
        return DB.Dimension
    return get_elementid_value(element.Category.Id)


def collector_for(element):
    collector = DB.FilteredElementCollector(revit.doc)
    if isinstance(element, DB.Dimension):
        collector = collector.OfClass(DB.Dimension)
    else:
        collector = collector.OfCategoryId(element.Category.Id)
    return collector.WhereElementIsNotElementType()


def wanted_type_values_by_collector(selected_elements):
    wanted = {}
    for element in selected_elements:
        if isinstance(element, DB.Dimension) or element.Category:
            values = wanted.setdefault(collector_key(element), (element, set()))[1]
            values.add(type_value(element))
    return wanted


def matching_elements(selected_elements):
    matches = []
    for representative, values in wanted_type_values_by_collector(
        selected_elements
    ).values():
        for element in collector_for(representative):
            if type_value(element) in values:
                matches.append(element)
    return matches


def element_rows(elements):
    return [
        [output.linkify(element.Id), element.GetType().Name] for element in elements
    ]


def print_element_table(title, elements):
    output.print_table(
        table_data=element_rows(elements),
        title=title,
        columns=[_t("column_id"), _t("column_class")],
    )


def print_matches(matches):
    model_elements = [element for element in matches if not element.ViewSpecific]
    if model_elements:
        print_element_table(
            _t("model_elements").format(len(model_elements)), model_elements
        )
    elements_by_view = {}
    for element in matches:
        if element.ViewSpecific:
            view_name = revit.query.get_name(revit.doc.GetElement(element.OwnerViewId))
            elements_by_view.setdefault(view_name, []).append(element)
    for view_name in sorted(elements_by_view):
        view_elements = elements_by_view[view_name]
        print_element_table(
            _t("view_elements").format(
                escape_for_output(view_name), len(view_elements)
            ),
            view_elements,
        )


def main():
    selected_elements = revit.get_selection().elements
    if not selected_elements:
        forms.alert(_t("no_selection"), exitscript=True)
    matches = matching_elements(selected_elements)
    if not matches:
        forms.alert(_t("no_suitable"), exitscript=True)
    if EXEC_PARAMS.config_mode:
        print_matches(matches)
    revit.get_selection().set_to([element.Id for element in matches])


if __name__ == "__main__":
    main()
