# -*- coding: utf-8 -*-
"""Lists all roof slopes in the model."""

from pyrevit import forms, script
from pyrevit import revit, DB
from pyrevit.coreutils import applocales
from pyrevit.revit import query

output = script.get_output()

RESOURCES = script.get_bundle_file("resources.xaml")


def _t(key):
    return applocales.get_locale_string_from_xaml(RESOURCES, key)


def collect_footprint_roofs():
    roofs = query.get_elements_by_categories([DB.BuiltInCategory.OST_Roofs])
    return [roof for roof in roofs if isinstance(roof, DB.FootPrintRoof)]


def iter_sloped_edges(roof):
    for profile in roof.GetProfiles():
        for curve in profile:
            if roof.DefinesSlope[curve]:
                yield curve


def group_roofs_by_slope(roofs):
    """Map each distinct displayed slope to its roofs.

    Returns:
        dict: ``{displayed slope: (slope angle, {element id text: element id})}``.
            Slopes are grouped by their formatted text so that two angles that
            display identically share one row.
    """
    roofs_by_slope = {}
    for roof in roofs:
        for curve in iter_sloped_edges(roof):
            slope = roof.SlopeAngle[curve]
            _, roof_ids = roofs_by_slope.setdefault(
                revit.units.format_slope(slope), (slope, {})
            )
            roof_ids[roof.Id.ToString()] = roof.Id
    return roofs_by_slope


roofs_by_slope = group_roofs_by_slope(collect_footprint_roofs())
if not roofs_by_slope:
    forms.alert(_t("no_sloped_roofs"), exitscript=True)

rows = []
for displayed_slope, (_, roof_ids) in sorted(
    roofs_by_slope.items(), key=lambda item: item[1][0]
):
    rows.append(
        [
            displayed_slope,
            len(roof_ids),
            " ".join(output.linkify(roof_id) for roof_id in roof_ids.values()),
        ]
    )
output.print_table(
    table_data=rows,
    title=_t("table_title"),
    columns=[_t("column_slope"), _t("column_count"), _t("column_roofs")],
)
