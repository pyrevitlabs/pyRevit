# -*- coding: utf-8 -*-
"""Count the triangles of every family type, or of every form in a family, at each detail level."""

from pyrevit import forms, script
from pyrevit import revit, DB
from pyrevit.coreutils import applocales, escape_for_output

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
    with forms.ProgressBar(
        title=_t("progress_title"), cancellable=True, step=10
    ) as progress:
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


def count_triangles_per_visibility(form):
    """Return the triangle counts of a form at coarse, medium and fine detail.

    The form is triangulated once, because Options.DetailLevel does not change the
    geometry of a form in a family document. The count then applies to each detail
    level the form is set to be visible in.
    """
    triangles = count_triangles(form, DB.ViewDetailLevel.Medium)
    visibility = form.GetVisibility()
    shown = [
        visibility.IsShownInCoarse,
        visibility.IsShownInMedium,
        visibility.IsShownInFine,
    ]
    return [triangles if is_shown else 0 for is_shown in shown]


def collect_family_counts():
    """Return one row per element of the family being edited with at least one triangle.

    Rows cover the family's own forms and every nested family instance, since each
    instance adds its triangles to the family. Each row holds the element and the
    triangle counts at coarse, medium and fine detail.
    """
    family_forms = revit.query.get_elements_by_class(DB.GenericForm, doc=revit.doc)
    nested_instances = revit.query.get_elements_by_class(
        DB.FamilyInstance, doc=revit.doc
    )
    rows = []
    counts_by_type = {}
    with forms.ProgressBar(
        title=_t("progress_title"), cancellable=True, step=10
    ) as progress:
        total = len(family_forms) + len(nested_instances)
        for index, form in enumerate(family_forms):
            if progress.cancelled:
                script.exit()
            progress.update_progress(index, total)
            counts = count_triangles_per_visibility(form)
            if any(counts):
                rows.append((form, counts))
        for index, instance in enumerate(nested_instances, len(family_forms)):
            if progress.cancelled:
                script.exit()
            progress.update_progress(index, total)
            type_id = instance.GetTypeId()
            if type_id not in counts_by_type:
                counts_by_type[type_id] = count_triangles_per_level(instance)
            counts = counts_by_type[type_id]
            if any(counts):
                rows.append((instance, counts))
    return rows


def element_label(element):
    if isinstance(element, DB.GenericForm):
        return element.GetType().Name
    return element.Name


def category_label(element):
    category = element.Category
    if category is None and revit.doc.IsFamilyDocument:
        category = revit.doc.OwnerFamily.FamilyCategory
    return category.Name if category else ""


def report(element_counts, title_key, name_column_key):
    fine_detail_index = DETAIL_LEVELS.index(DB.ViewDetailLevel.Fine)
    element_counts = sorted(element_counts, key=lambda row: row[1][fine_detail_index])
    table_data = [
        [
            escape_for_output(element_label(element)),
            escape_for_output(category_label(element)),
            output.linkify(element.Id),
        ]
        + counts
        for element, counts in element_counts
    ]
    table_data.append(
        [_t("grand_total"), "", ""]
        + [sum(counts[index] for _, counts in element_counts) for index in range(3)]
    )
    output.print_table(
        table_data,
        title=_t(title_key),
        columns=[
            _t(name_column_key),
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
    if revit.doc.IsFamilyDocument:
        element_counts = collect_family_counts()
        if not element_counts:
            forms.alert(_t("no_geometry_family"), exitscript=True)
        report(element_counts, "table_title_family", "column_form")
    else:
        element_counts = collect_type_counts()
        if not element_counts:
            forms.alert(_t("no_geometry"), exitscript=True)
        report(element_counts, "table_title", "column_type")


if __name__ == "__main__":
    main()
