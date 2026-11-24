# -*- coding: utf-8 -*-
"""Select the elements that share a category with the selected elements.

Searches the active view, or the whole project on Shift-click.
"""

from pyrevit import forms, script
from pyrevit import EXEC_PARAMS, revit, DB
from pyrevit.coreutils import applocales
from pyrevit.framework import to_clr_list

RESOURCES = script.get_bundle_file("resources.xaml")


def _t(key):
    return applocales.get_locale_string_from_xaml(RESOURCES, key)


def selected_category_ids():
    return {
        element.Category.Id
        for element in revit.get_selection().elements
        if element.Category
    }


def main():
    if not EXEC_PARAMS.config_mode:
        forms.check_graphicalview(revit.active_view, exitscript=True)
    category_ids = selected_category_ids()
    if not category_ids:
        forms.alert(_t("no_suitable"), exitscript=True)
    if EXEC_PARAMS.config_mode:
        collector = DB.FilteredElementCollector(revit.doc)
    else:
        collector = DB.FilteredElementCollector(revit.doc, revit.active_view.Id)
    similar_ids = (
        collector.WhereElementIsNotElementType()
        .WherePasses(
            DB.ElementMulticategoryFilter(to_clr_list(DB.ElementId, category_ids))
        )
        .ToElementIds()
    )
    revit.get_selection().set_to(similar_ids)


if __name__ == "__main__":
    main()
