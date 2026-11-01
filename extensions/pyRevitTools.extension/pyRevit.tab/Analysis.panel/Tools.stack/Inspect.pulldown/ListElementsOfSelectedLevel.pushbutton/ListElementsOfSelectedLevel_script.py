# -*- coding: utf-8 -*-
"""List all Elements of the selected level(s)."""

from collections import defaultdict

from pyrevit import forms, script
from pyrevit import revit, DB
from pyrevit.coreutils import applocales

from outputtext import escape_for_output

output = script.get_output()

RESOURCES = script.get_bundle_file("resources.xaml")


def _t(key):
    return applocales.get_locale_string_from_xaml(RESOURCES, key)


def group_elements_by_level():
    elements_by_level = defaultdict(list)
    all_elements = DB.FilteredElementCollector(revit.doc).WhereElementIsNotElementType()
    for element in all_elements:
        elements_by_level[element.LevelId].append(element)
    return elements_by_level


def group_by_category(elements):
    elements_by_category = defaultdict(list)
    for element in elements:
        category_name = element.Category.Name if element.Category else _t("no_category")
        elements_by_category[category_name].append(element)
    return elements_by_category


def print_category_elements(category_name, elements):
    output.print_html(
        "<details><summary>{}: {}</summary>{}</details>".format(
            escape_for_output(category_name),
            len(elements),
            "<br>".join(output.linkify(element.Id) for element in elements),
        )
    )


def report_level(level, elements):
    elements_by_category = group_by_category(elements)
    category_items = sorted(elements_by_category.items(), key=lambda item: item[0])
    output.print_md(
        "### {}".format(_t("elements_on_level").format(escape_for_output(level.Name)))
    )
    if not elements:
        output.print_md("**{}**".format(_t("no_elements")))
        return
    output.print_table(
        table_data=[
            [
                escape_for_output(category_name),
                len(category_elements),
                output.linkify(
                    [element.Id for element in category_elements],
                    title=_t("select_all"),
                ),
            ]
            for category_name, category_elements in category_items
        ],
        title=_t("table_title").format(len(elements_by_category), len(elements)),
        columns=[_t("column_category"), _t("column_count"), _t("column_select")],
    )
    for category_name, category_elements in category_items:
        print_category_elements(category_name, category_elements)


def main():
    levels = forms.select_levels(use_selection=True)
    if not levels:
        forms.alert(_t("select_levels"), exitscript=True)
    elements_by_level = group_elements_by_level()
    output.print_md("#### {}".format(_t("list_elements_title")))
    for level in levels:
        report_level(level, elements_by_level[level.Id])


if __name__ == "__main__":
    main()
