# -*- coding: utf-8 -*-
"""List all elements that are tied to the selected element."""

from pyrevit import script
from pyrevit import revit, DB
from pyrevit.coreutils import applocales

from outputtext import escape_for_output

output = script.get_output()

RESOURCES = script.get_bundle_file("resources.xaml")
EMPTY_CELL = "–"


def _t(key):
    return applocales.get_locale_string_from_xaml(RESOURCES, key)


def find_dependent_element_ids(element_id):
    """Return the ids Revit would delete together with the element.

    The deletion runs in a dry transaction that is always rolled back, so the
    model is not changed.
    """
    with revit.DryTransaction("Search for linked elements"):
        return list(revit.doc.Delete(element_id))


def describe(element, selected_ids):
    category_name = element.Category.Name if element.Category else ""
    family_and_type = ""
    if isinstance(element, DB.FamilyInstance):
        family_and_type = "{}: {}".format(
            revit.query.get_family_name(element), revit.query.get_symbol_name(element)
        )
    note = _t("selected_object") if element.Id in selected_ids else ""
    return [
        output.linkify(element.Id),
        element.GetType().Name,
        escape_for_output(category_name),
        escape_for_output(family_and_type) or EMPTY_CELL,
        note or EMPTY_CELL,
    ]


def main():
    selection = revit.get_selection()
    selected_element = selection.first
    dependent_ids = find_dependent_element_ids(selected_element.Id)
    output.print_md(
        "### {}".format(
            _t("tied_to_element").format(output.linkify(selected_element.Id))
        )
    )
    rows = [
        describe(element, selection.element_ids)
        for element in (
            revit.doc.GetElement(element_id) for element_id in dependent_ids
        )
        if element
    ]
    output.print_table(
        table_data=rows,
        title=_t("table_title").format(len(rows)),
        columns=[
            _t("column_element"),
            _t("column_class"),
            _t("column_category"),
            _t("column_family_type"),
            _t("column_note"),
        ],
    )


if __name__ == "__main__":
    main()
