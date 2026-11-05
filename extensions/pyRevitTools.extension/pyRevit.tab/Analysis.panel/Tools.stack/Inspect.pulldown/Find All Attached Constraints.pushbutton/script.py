# -*- coding: utf-8 -*-
"""Find all constraints attached to the selected element."""

from pyrevit import script
from pyrevit import revit, DB
from pyrevit.coreutils import applocales, escape_for_output

output = script.get_output()

RESOURCES = script.get_bundle_file("resources.xaml")


def _t(key):
    return applocales.get_locale_string_from_xaml(RESOURCES, key)


def collect_constraints():
    return list(
        DB.FilteredElementCollector(revit.doc)
        .OfCategory(DB.BuiltInCategory.OST_Constraints)
        .WhereElementIsNotElementType()
    )


def category_name_of(element_id):
    element = revit.doc.GetElement(element_id)
    if element and element.Category:
        return escape_for_output(element.Category.Name)
    return _t("unknown_category")


def reference_rows(constraint, selected_id):
    rows = []
    for reference in constraint.References:
        element_label = output.linkify(reference.ElementId)
        if reference.ElementId == selected_id:
            element_label = "{} ({})".format(element_label, _t("this_element"))
        rows.append(
            [
                output.linkify(constraint.Id),
                constraint.GetType().Name,
                str(reference.ElementReferenceType),
                category_name_of(reference.ElementId),
                element_label,
            ]
        )
    return rows


def report(selected_element, constraints):
    attached = [
        constraint
        for constraint in constraints
        if selected_element.Id in [ref.ElementId for ref in constraint.References]
    ]
    output.print_md(
        "### {}".format(
            _t("constraints_of_element").format(output.linkify(selected_element.Id))
        )
    )
    if not attached:
        output.print_md(_t("no_constraints"))
        return
    output.print_table(
        table_data=[
            row
            for constraint in attached
            for row in reference_rows(constraint, selected_element.Id)
        ],
        title=_t("table_title").format(len(attached)),
        columns=[
            _t("column_constraint"),
            _t("column_constraint_type"),
            _t("column_reference_type"),
            _t("column_category"),
            _t("column_element"),
        ],
    )


def main():
    constraints = collect_constraints()
    for selected_element in revit.get_selection().elements:
        report(selected_element, constraints)


if __name__ == "__main__":
    main()
