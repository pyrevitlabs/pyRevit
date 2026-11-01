# -*- coding: utf-8 -*-
"""Count the triangles of every family type at each detail level."""

from pyrevit import forms, script
from pyrevit import revit, DB
from pyrevit.coreutils import applocales

from outputtext import escape_for_output

logger = script.get_logger()
output = script.get_output()

RESOURCES = script.get_bundle_file("resources.xaml")
DETAIL_LEVELS = [
    DB.ViewDetailLevel.Coarse,
    DB.ViewDetailLevel.Medium,
    DB.ViewDetailLevel.Fine,
]


def _t(key):
    return applocales.get_locale_string_from_xaml(RESOURCES, key)


def count_triangles(element, detail_level):
    triangles = 0
    for geometry in revit.query.get_geometry(element, detail_level=detail_level):
        if isinstance(geometry, DB.Solid) and geometry.Faces.Size > 0:
            for face in geometry.Faces:
                mesh = face.Triangulate()
                if mesh is not None:
                    triangles += mesh.NumTriangles
    return triangles


def count_triangles_per_level(element):
    counts = []
    for detail_level in DETAIL_LEVELS:
        try:
            counts.append(count_triangles(element, detail_level))
        except Exception:
            logger.debug(
                "Triangles of element {} at {} detail could not be counted.".format(
                    element.Id, detail_level
                )
            )
            counts.append(0)
    return counts


def collect_type_counts():
    """Return one row per family type with at least one triangle.

    Each row holds the first instance found, which stands in for its type, and the
    triangle counts at coarse, medium and fine detail.
    """
    instances = revit.query.get_elements_by_class(DB.FamilyInstance, doc=revit.doc)
    rows = {}
    with forms.ProgressBar(title=_t("progress_title"), cancellable=True) as progress:
        for index, instance in enumerate(instances):
            if progress.cancelled:
                script.exit()
            progress.update_progress(index, len(instances))
            type_id = instance.GetTypeId()
            if type_id in rows:
                continue
            counts = count_triangles_per_level(instance)
            if any(counts):
                rows[type_id] = (instance, counts)
    return list(rows.values())


def report(type_counts):
    fine_detail_index = DETAIL_LEVELS.index(DB.ViewDetailLevel.Fine)
    type_counts = sorted(type_counts, key=lambda row: row[1][fine_detail_index])
    table_data = [
        [
            escape_for_output(instance.Name),
            escape_for_output(instance.Category.Name),
            output.linkify(instance.Id),
        ]
        + counts
        for instance, counts in type_counts
    ]
    table_data.append(
        [_t("grand_total"), "", ""]
        + [sum(counts[index] for _, counts in type_counts) for index in range(3)]
    )
    output.print_table(
        table_data,
        title=_t("table_title"),
        columns=[
            _t("column_type"),
            _t("column_category"),
            _t("column_example"),
            _t("column_coarse"),
            _t("column_medium"),
            _t("column_fine"),
        ],
        last_line_style="color:white;font-weight: bolder; background-color: gray;",
    )


def main():
    output.close_others()
    type_counts = collect_type_counts()
    if not type_counts:
        forms.alert(_t("no_geometry"), exitscript=True)
    report(type_counts)


if __name__ == "__main__":
    main()
