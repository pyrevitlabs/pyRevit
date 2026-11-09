# -*- coding: utf-8 -*-
"""List the views referenced by the selected elevation tag."""

from pyrevit import forms, script
from pyrevit import revit, DB
from pyrevit.coreutils import applocales, escape_for_output

output = script.get_output()

RESOURCES = script.get_bundle_file("resources.xaml")


def _t(key):
    return applocales.get_locale_string_from_xaml(RESOURCES, key)


def referenced_views(elevation_marker):
    """Yield the views of the marker.

    Note:
        Views occupy fixed slots of the marker, so a marker with one view can
        hold it in any slot up to ``MaximumViewCount``. All slots are visited.
    """
    for index in range(elevation_marker.MaximumViewCount):
        view = revit.doc.GetElement(elevation_marker.GetViewId(index))
        if view:
            yield view


def view_row(view):
    detail_number = view.get_Parameter(DB.BuiltInParameter.VIEWER_DETAIL_NUMBER)
    return [
        (detail_number.AsString() if detail_number else "") or "",
        escape_for_output(revit.query.get_name(view)),
        str(view.ViewType),
        _t("yes") if view.IsTemplate else _t("no"),
        output.linkify(view.Id),
    ]


def main():
    elevation_marker = revit.get_selection().first
    if not isinstance(elevation_marker, DB.ElevationMarker):
        forms.alert(_t("select_elevation_tag"), exitscript=True)
    views = list(referenced_views(elevation_marker))
    if not views:
        output.print_md("**{}**".format(_t("no_views")))
        return
    output.print_table(
        table_data=[view_row(view) for view in views],
        title=_t("table_title"),
        columns=[
            _t("column_detail_number"),
            _t("column_name"),
            _t("column_view_type"),
            _t("column_template"),
            _t("column_show"),
        ],
    )


if __name__ == "__main__":
    main()
