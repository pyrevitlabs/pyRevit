# -*- coding: utf-8 -*-
"""List the Revit links that the selected elements monitor."""

from pyrevit import script
from pyrevit import revit, DB
from pyrevit.coreutils import applocales

from outputtext import escape_for_output

output = script.get_output()

RESOURCES = script.get_bundle_file("resources.xaml")


def _t(key):
    return applocales.get_locale_string_from_xaml(RESOURCES, key)


def monitored_link_rows(element):
    rows = []
    for link_id in element.GetMonitoredLinkElementIds():
        link = revit.doc.GetElement(link_id)
        if isinstance(link, DB.RevitLinkInstance):
            rows.append([output.linkify(element.Id), escape_for_output(link.Name)])
    return rows


def main():
    rows = [
        row for element in revit.get_selection() for row in monitored_link_rows(element)
    ]
    if not rows:
        output.print_md("**{}**".format(_t("no_monitored_links")))
        return
    output.print_table(
        table_data=rows,
        title=_t("table_title"),
        columns=[_t("column_element"), _t("column_link")],
    )


if __name__ == "__main__":
    main()
