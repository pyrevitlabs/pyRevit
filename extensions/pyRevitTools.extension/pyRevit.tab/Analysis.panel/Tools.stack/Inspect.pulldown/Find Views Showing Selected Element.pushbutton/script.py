# -*- coding: utf-8 -*-
"""List all views that the selected elements are visible in."""

from pyrevit import forms, script
from pyrevit import revit, DB
from pyrevit.coreutils import applocales

from outputtext import escape_for_output

output = script.get_output()

RESOURCES = script.get_bundle_file("resources.xaml")


def _t(key):
    return applocales.get_locale_string_from_xaml(RESOURCES, key)


def collect_views():
    views = (
        DB.FilteredElementCollector(revit.doc)
        .OfCategory(DB.BuiltInCategory.OST_Views)
        .WhereElementIsNotElementType()
    )
    return [view for view in views if not view.IsTemplate]


def count_selected_elements_in(view, selected_ids):
    view_element_ids = set(
        DB.FilteredElementCollector(revit.doc, view.Id)
        .WhereElementIsNotElementType()
        .ToElementIds()
    )
    return len(view_element_ids & selected_ids)


def find_showing_views(selected_ids):
    """Return (view, matching element count) for every view showing a selected element."""
    views = collect_views()
    showing_views = []
    with forms.ProgressBar(title=_t("progress_title"), cancellable=True) as progress:
        for index, view in enumerate(views):
            if progress.cancelled:
                break
            progress.update_progress(index, len(views))
            matches = count_selected_elements_in(view, selected_ids)
            if matches:
                showing_views.append((view, matches))
    return showing_views


def main():
    selected_ids = set(revit.get_selection().element_ids)
    showing_views = find_showing_views(selected_ids)
    output.print_md("### {}".format(_t("views_containing")))
    if not showing_views:
        output.print_md("**{}**".format(_t("no_views")))
        return
    output.print_table(
        table_data=[
            [
                escape_for_output(revit.query.get_name(view)),
                str(view.ViewType),
                matches,
                output.linkify(view.Id),
            ]
            for view, matches in showing_views
        ],
        title=_t("table_title").format(len(showing_views)),
        columns=[
            _t("column_view"),
            _t("column_view_type"),
            _t("column_matches"),
            _t("column_show"),
        ],
    )


if __name__ == "__main__":
    main()
