# -*- coding: utf-8 -*-
"""Place three model lines intersecting at the centroid of the selected elements."""

from pyrevit import EXEC_PARAMS
from pyrevit import forms, script
from pyrevit import revit, DB
from pyrevit.coreutils import applocales
from pyrevit.revit import query
from Autodesk.Revit.Exceptions import InvalidOperationException

logger = script.get_logger()

RESOURCES = script.get_bundle_file("resources.xaml")


def _t(key):
    return applocales.get_locale_string_from_xaml(RESOURCES, key)


def merge_solids(solids):
    """Merge the solids into one by boolean union.

    Solids that fail to merge are logged and left out of the result.

    Args:
        solids (list[DB.Solid]): Non-empty list of solids.

    Returns:
        DB.Solid: The union of the solids.
    """
    union = None
    for solid in solids:
        if not union:
            union = solid
            continue
        try:
            union = DB.BooleanOperationsUtils.ExecuteBooleanOperation(
                union, solid, DB.BooleanOperationsType.Union
            )
        except InvalidOperationException:
            logger.error(
                "Failed to merge solid from element {}, "
                "it will be excluded from the calculation".format(
                    revit.ElementWrapper(solid_owner(solid)).name
                )
            )
    return union


def solid_owner(solid):
    stable_reference = solid.Faces[0].Reference.ConvertToStableRepresentation(revit.doc)
    return revit.doc.GetElement(stable_reference.split(":")[0])


def collect_solids(elements):
    solids = []
    for element in elements:
        logger.debug("processing {}".format(element.Name))
        solids.extend(
            geometry
            for geometry in query.get_geometry(element, compute_references=True)
            if isinstance(geometry, DB.Solid) and geometry.Faces.Size > 0
        )
    return solids


def collect_line_styles():
    line_category = revit.doc.Settings.Categories.get_Item(DB.BuiltInCategory.OST_Lines)
    line_styles = [
        subcategory.GetGraphicsStyle(DB.GraphicsStyleType.Projection)
        for subcategory in line_category.SubCategories
    ]
    return sorted(line_styles, key=lambda style: style.Name)


def load_configured_line_style(line_styles):
    configured_name = script.get_config().get_option("line_style", None)
    logger.debug("configured line style: {}".format(configured_name))
    return next((style for style in line_styles if style.Name == configured_name), None)


def choose_line_style(line_styles):
    line_style = forms.SelectFromList.show(
        line_styles, name_attr="Name", title=_t("select_line_style")
    )
    if not line_style:
        script.exit()
    config = script.get_config()
    config.line_style = line_style.Name
    script.save_config()
    return line_style


def place_centroid_marker(centroid, line_style):
    with revit.Transaction(_t("transaction_name")):
        horizontal_plane = DB.SketchPlane.Create(
            revit.doc, DB.Plane.CreateByNormalAndOrigin(DB.XYZ.BasisZ, centroid)
        )
        vertical_plane = DB.SketchPlane.Create(
            revit.doc, DB.Plane.CreateByNormalAndOrigin(DB.XYZ.BasisY, centroid)
        )
        axes = (
            (DB.XYZ.BasisX, horizontal_plane),
            (DB.XYZ.BasisY, horizontal_plane),
            (DB.XYZ.BasisZ, vertical_plane),
        )
        for direction, sketch_plane in axes:
            line = DB.Line.CreateBound(centroid - direction, centroid + direction)
            model_line = revit.doc.Create.NewModelCurve(line, sketch_plane)
            if line_style:
                model_line.LineStyle = line_style


def main():
    selection = revit.get_selection()
    if not selection:
        forms.alert(_t("select_element"), exitscript=True)

    line_styles = collect_line_styles()
    if EXEC_PARAMS.config_mode:
        line_style = choose_line_style(line_styles)
    else:
        line_style = load_configured_line_style(line_styles)

    solids = collect_solids(selection)
    if not solids:
        forms.alert(_t("no_solid_geometry"), exitscript=True)

    place_centroid_marker(merge_solids(solids).ComputeCentroid(), line_style)


main()
