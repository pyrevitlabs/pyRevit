# -*- coding: utf-8 -*-
"""Analysis Visualization Framework (AVF) helpers.

Utilities for displaying arbitrary numeric values on elements in a view,
using Revit's SpatialFieldManager / AVF. Useful for heatmaps, KPI overlays,
QA/QC markers, or any "paint a number onto elements" workflow.

Typical usage::

    from pyrevit import revit
    from pyrevit.revit import avf

    values = {wall1: 12.5, wall2: 44.0}
    # use get_or_create_colored_surface_display_style(...) instead for a
    # gradient/heatmap look rather than text markers (3D views only)
    style = avf.get_or_create_marker_display_style(revit.doc, "MyTool_AVF")
    with revit.Transaction("Show values"):
        revit.active_view.AnalysisDisplayStyleId = style.Id
        results = avf.display_avf_values(values, revit.active_view, unit="ea")

Notes / known limitations:
    - Values are drawn only if the view has an AnalysisDisplayStyle
      assigned (``View.AnalysisDisplayStyleId``). The display functions do
      not assign one.
    - Marker size belongs to the display style, not to the values:
      ``AnalysisDisplayMarkersAndTextSettings.MarkerSize`` is a length on
      paper in Revit internal units (feet). A marker spans about
      ``MarkerSize * view.Scale`` feet in the model. The API default is
      1/96 ft (about 3.2 mm on paper); for a size in millimetres assign
      ``millimetres / 304.8``.
    - Values are anchored to faces only in 3D views without an active
      section box, for elements visible in that view. Everywhere else they
      are placed at the element's bounding-box center, which text markers
      draw but a colored-surface style cannot paint.
    - Face selection uses the largest planar-or-curved face turned toward
      the viewer. It is sampled at its UV-bounding-box center, which is an
      approximation for strongly curved faces (cylinders, etc.) and can
      fall into an opening.
    - SpatialFieldManager results (the actual point/value data) are NOT
      saved with the document - they live only for the current session
      and are gone on reopen even without calling ``clear_avf_results``.
      What IS saved with the model is the AnalysisDisplayStyle itself and
      its assignment to a view (``View.AnalysisDisplayStyleId``), so a
      view can "remember" how it should render results without remembering
      the results. Call ``clear_avf_results`` to remove results within a
      session (e.g. before recomputing).
    - Rolling a transaction group back does not reliably remove AVF
      results.
    - Two display styles are provided: ``get_or_create_marker_display_style``
      (text markers, good for discrete/inspectable values) and
      ``get_or_create_colored_surface_display_style`` (gradient heatmap,
      good for continuous/comparative values).
    - The write functions open their own transaction, which becomes a
      SubTransaction when one is already open on the active document.
"""

from pyrevit import DB
from pyrevit import PyRevitException
from pyrevit.revit import Transaction, query
from pyrevit.framework import List, System
from pyrevit.coreutils.logger import get_logger
from pyrevit.compat import get_elementid_value_func

get_elementid_value = get_elementid_value_func()

mlogger = get_logger(__name__)

_FACING_TOLERANCE = 1e-6

__all__ = (
    "get_face_facing_direction",
    "clear_avf_results",
    "display_avf_values",
    "display_avf_values_at_points",
    "update_avf_values",
    "remove_avf_primitive",
    "get_or_create_marker_display_style",
    "get_or_create_colored_surface_display_style",
)


def get_face_facing_direction(
    element,
    direction,
    detail_level=DB.ViewDetailLevel.Coarse,
):
    """Find the largest face of ``element`` that faces the viewer.

    A face faces the viewer when its outward normal points along
    ``direction``.

    Args:
        element (DB.Element): Element to inspect.
        direction (DB.XYZ): Direction pointing toward the viewer, e.g.
            ``view.ViewDirection``.
        detail_level (DB.ViewDetailLevel, optional): Geometry detail
            level to extract. Defaults to Coarse. Some families have no
            solid faces at the coarser levels.

    Returns:
        DB.Face: The best-matching face, or None if the element has no
            solid geometry, or no face is oriented toward the viewer.

    Warning:
        Passing the reference of a face that the view does not show to
        ``SpatialFieldManager.AddSpatialFieldPrimitive`` can crash Revit,
        which no ``try``/``except`` can catch.
    """
    geom_elem = query.get_geometry(
        element, compute_references=True, detail_level=detail_level
    )
    if not geom_elem:
        return None

    direction = direction.Normalize()

    best_face = None
    best_area = -1.0

    for geom_obj in geom_elem:
        if not isinstance(geom_obj, DB.Solid) or not geom_obj.Faces:
            continue
        for face in geom_obj.Faces:
            area = face.Area
            if area <= 0 or area <= best_area:
                continue
            uv_center = _get_uv_center(face)
            try:
                normal = face.ComputeNormal(uv_center).Normalize()
            except Exception:
                continue
            if normal.DotProduct(direction) > _FACING_TOLERANCE:
                best_area = area
                best_face = face

    return best_face


def _get_uv_center(face):
    bbox = face.GetBoundingBox()
    return DB.UV(
        (bbox.Min.U + bbox.Max.U) / 2.0,
        (bbox.Min.V + bbox.Max.V) / 2.0,
    )


def _can_anchor_to_faces(view):
    return isinstance(view, DB.View3D) and not view.IsSectionBoxActive


def _get_face_candidate_ids(elements, view):
    """Return the id values of *elements* whose faces may be handed to Revit.

    Runs one view-bound collector for all elements, because each such query
    can take seconds on a view that has to be regenerated.
    """
    if not elements or not _can_anchor_to_faces(view):
        return set()
    element_ids = List[DB.ElementId]()
    for element in elements:
        element_ids.Add(element.Id)
    visible_ids = (
        DB.FilteredElementCollector(view.Document, view.Id)
        .WherePasses(DB.ElementIdSetFilter(element_ids))
        .ToElementIds()
    )
    return set(get_elementid_value(element_id) for element_id in visible_ids)


def _get_face_anchor(element, view):
    detail_level = view.DetailLevel
    if detail_level == DB.ViewDetailLevel.Undefined:
        detail_level = DB.ViewDetailLevel.Medium
    face = get_face_facing_direction(
        element, view.ViewDirection, detail_level=detail_level
    )
    if face is None or face.Reference is None:
        return None
    return face.Reference, _get_uv_center(face)


def _get_center(element, view):
    bbox = element.get_BoundingBox(view)
    if bbox is None:
        return None
    return (bbox.Min + bbox.Max) / 2.0


def _resolve_anchors(element_value_dict, view, face_candidate_ids):
    """Read every element's face anchor and center before anything is added.

    Adding a primitive makes the next geometry or view query regenerate,
    which can take seconds, so no query may run between two primitives.
    """
    anchors = []
    for element, value in element_value_dict.items():
        elem_id = get_elementid_value(element.Id)
        try:
            face_anchor = (
                _get_face_anchor(element, view)
                if elem_id in face_candidate_ids
                else None
            )
            anchors.append((elem_id, value, face_anchor, _get_center(element, view)))
        except Exception as ex:
            mlogger.exception("Error reading element ID {}: {}".format(elem_id, ex))
            anchors.append((elem_id, value, None, None))
    return anchors


def _add_face_primitive(sfm, reference, uv):
    try:
        sfp_id = sfm.AddSpatialFieldPrimitive(reference)
    except Exception as ex:
        mlogger.debug("Revit rejected a face reference: {}".format(ex))
        return None
    uv_list = List[DB.UV]()
    uv_list.Add(uv)
    return sfp_id, DB.Analysis.FieldDomainPointsByUV(uv_list)


def _add_point_primitive(sfm, point):
    sfp_id = sfm.AddSpatialFieldPrimitive()
    xyz_list = List[DB.XYZ]()
    xyz_list.Add(point)
    return sfp_id, DB.Analysis.FieldDomainPointsByXYZ(xyz_list)


def _get_or_create_sfm(view, number_of_measurements=1):
    """Get the existing SpatialFieldManager for a view, or create one.

    Args:
        view (DB.View): View to attach the SFM to. Must be a view type
            that supports AVF (3D, plan, section, elevation, detail).
        number_of_measurements (int, optional): Length of the value
            array in each ValueAtPoint. Defaults to 1.

    Returns:
        DB.Analysis.SpatialFieldManager
    """
    sfm = DB.Analysis.SpatialFieldManager.GetSpatialFieldManager(view)
    if sfm is None:
        try:
            sfm = DB.Analysis.SpatialFieldManager.CreateSpatialFieldManager(
                view, number_of_measurements
            )
        except Exception as ex:
            raise PyRevitException(
                "Could not create a SpatialFieldManager for view '{}'. "
                "Does this view type support AVF? ({})".format(view.Name, ex)
            )
    return sfm


def _get_or_create_schema(sfm, schema_name, schema_desc, units, visible=True):
    """Get an existing AVF result schema by name, or register a new one.

    Args:
        sfm (DB.Analysis.SpatialFieldManager): Manager to register on.
        schema_name (str): Name for the schema.
        schema_desc (str): Description for the schema.
        units (str or list[tuple[str, float]]): Either a single unit
            label (display-only, no conversion applied to your values),
            or a list of ``(unit_name, multiplier)`` pairs to let the
            viewer toggle between multiple display units of the same
            underlying value - e.g. ``[("Feet", 1), ("Inches", 12)]``.
        visible (bool, optional): Whether the schema is visible in the
            view's AVF legend/toggle list. Defaults to True.

    Returns:
        int: Schema id (result index), for use with
            ``UpdateSpatialFieldPrimitive``.
    """
    for sid in sfm.GetRegisteredResults():
        existing_schema = sfm.GetResultSchema(sid)
        if existing_schema.Name == schema_name:
            return sid

    try:
        text_types = (basestring,)  # noqa: F821
    except NameError:  # Python 3
        text_types = (str,)

    if isinstance(units, text_types):
        unit_pairs = [(units, 1)]
    else:
        unit_pairs = list(units)

    if not unit_pairs:
        raise PyRevitException(
            "Units must be a non-empty string or a non-empty list of (unit_name, multiplier) pairs."
        )

    unit_names = [unit_name for unit_name, _ in unit_pairs]
    if any(not name for name in unit_names) or len(set(unit_names)) != len(unit_names):
        raise PyRevitException(
            "Unit names must be non-empty and unique. Got: {}".format(unit_names)
        )

    unit_name_list = List[System.String]()
    unit_multiplier_list = List[System.Double]()
    for unit_name, multiplier in unit_pairs:
        unit_name_list.Add(unit_name)
        unit_multiplier_list.Add(System.Double(multiplier))
    schema = DB.Analysis.AnalysisResultSchema(schema_name, schema_desc)
    schema.SetUnits(unit_name_list, unit_multiplier_list)
    schema.IsVisible = visible
    return sfm.RegisterResult(schema)


def clear_avf_results(view):
    """Clear all AVF results from a view.

    Args:
        view (DB.View): The view to clear results from.

    Note:
        AVF result data is not saved with the document at all, so this
        is only needed to clear results within the current session (e.g.
        before recomputing). The AnalysisDisplayStyle assigned to the
        view is unaffected and does persist with the model.
    """
    sfm = DB.Analysis.SpatialFieldManager.GetSpatialFieldManager(view)
    if sfm:
        with Transaction("Clear AVF Results"):
            sfm.Clear()


def _make_field_values(value):
    val_double_list = List[System.Double]()
    val_double_list.Add(System.Double(value))
    val_at_point = DB.Analysis.ValueAtPoint(val_double_list)
    val_list = List[DB.Analysis.ValueAtPoint]()
    val_list.Add(val_at_point)
    return DB.Analysis.FieldValues(val_list)


def display_avf_values(
    element_value_dict,
    view,
    schema_name="pyRevitAVF",
    schema_desc="AVF values from pyRevit",
    unit="Value",
    use_bbox_center=False,
    visible=True,
):
    """Display numeric values on multiple elements in a view.

    Args:
        element_value_dict (dict[DB.Element, float]): Element -> value.
        view (DB.View): View to display values in.
        schema_name (str, optional): AVF schema name. Reused if a schema
            with this name already exists on the view. Defaults to
            "pyRevitAVF".
        schema_desc (str, optional): AVF schema description.
        unit (str or list[tuple[str, float]], optional): Single unit
            label, or a list of ``(unit_name, multiplier)`` pairs if you
            want the viewer to be able to toggle between multiple display
            units (see ``_get_or_create_schema``). Unit names must be non-empty
            and unique, as required by the Revit API. For dimensionless values,
            use a descriptive label such as ``"Value"`` or ``"Unitless"``.
            Defaults to ``"Value"``.
        use_bbox_center (bool, optional): Always use the element's
            bounding-box center as the insertion point. When False, a face
            turned toward the viewer is used where that is possible: a 3D
            view without an active section box, an element visible in it,
            and a face whose reference Revit accepts (references of family
            instance geometry are often rejected). Otherwise the
            bounding-box center is used as well. In a 3D view that is not
            the active one, each face anchor can make Revit regenerate,
            which took seconds per element in a large model; activate the
            view first or pass True. Defaults to False.
        visible (bool, optional): Whether the schema is visible/toggle-able
            in the view. Defaults to True.

    Returns:
        dict[int, tuple]: element-id-value -> (success, sfp_id). ``sfp_id``
            is None on failure. Feed this straight into
            ``update_avf_values`` for cheap repeated updates.
    """
    results = {}
    face_candidate_ids = (
        set()
        if use_bbox_center
        else _get_face_candidate_ids(list(element_value_dict), view)
    )
    anchors = _resolve_anchors(element_value_dict, view, face_candidate_ids)

    with Transaction("Display AVF Values"):
        sfm = _get_or_create_sfm(view)
        schema_id = _get_or_create_schema(
            sfm, schema_name, schema_desc, unit, visible=visible
        )

        for elem_id, value, face_anchor, center in anchors:
            try:
                primitive = (
                    _add_face_primitive(sfm, *face_anchor) if face_anchor else None
                )
                if primitive is None:
                    if center is None:
                        mlogger.warning(
                            "Element ID {} has no bounding box in view "
                            "'{}' (not visible?)".format(elem_id, view.Name)
                        )
                        results[elem_id] = (False, None)
                        continue
                    primitive = _add_point_primitive(sfm, center)
                sfp_id, domain_pts = primitive

                vals = _make_field_values(value)
                sfm.UpdateSpatialFieldPrimitive(sfp_id, domain_pts, vals, schema_id)
                results[elem_id] = (True, sfp_id)

            except Exception as ex:
                mlogger.exception(
                    "Error processing element ID {}: {}".format(elem_id, ex)
                )
                results[elem_id] = (False, None)

    return results


def update_avf_values(
    primitive_dict,
    element_value_dict,
    view,
    schema_name="pyRevitAVF",
    schema_desc="AVF values from pyRevit",
    unit="Value",
    visible=True,
):
    """Update values on primitives previously created by ``display_avf_values``.

    Cheaper than re-running ``display_avf_values`` since it reuses the
    existing primitive/face instead of re-searching geometry.

    Args:
        primitive_dict (dict[int, tuple]): Output of ``display_avf_values``,
            i.e. element-id-value -> (success, sfp_id).
        element_value_dict (dict[DB.Element, float]): Element -> new value.
        view (DB.View): View the primitives were created in.
        schema_name (str, optional): Must match the schema used originally.
        schema_desc (str, optional): AVF schema description.
        unit (str or list[tuple[str, float]], optional): Must match what
            was used when the schema was first created.
        visible (bool, optional): Whether the schema is visible. Defaults
            to True.

    Returns:
        dict[int, bool]: element-id-value -> success.
    """
    results = {}

    with Transaction("Update AVF Values"):
        sfm = _get_or_create_sfm(view)
        schema_id = _get_or_create_schema(
            sfm, schema_name, schema_desc, unit, visible=visible
        )

        for element, new_value in element_value_dict.items():
            elem_id = get_elementid_value(element.Id)

            entry = primitive_dict.get(elem_id)
            if not entry or not entry[0] or entry[1] is None:
                mlogger.error(
                    "No primitive data found for element ID: {}".format(elem_id)
                )
                results[elem_id] = False
                continue

            sfp_id = entry[1]
            try:
                vals = _make_field_values(new_value)
                sfm.UpdateSpatialFieldPrimitive(sfp_id, None, vals, schema_id)
                results[elem_id] = True
            except Exception as ex:
                mlogger.exception(
                    "Error updating element ID {}: {}".format(elem_id, ex)
                )
                results[elem_id] = False

    return results


def remove_avf_primitive(view, sfp_id):
    """Remove a single AVF primitive from a view.

    Args:
        view (DB.View): View the primitive belongs to.
        sfp_id (int): Primitive index, as returned by ``display_avf_values``.

    Returns:
        bool: True if removed, False if no SFM/primitive was found.
    """
    sfm = DB.Analysis.SpatialFieldManager.GetSpatialFieldManager(view)
    if sfm is None:
        return False
    with Transaction("Remove AVF Primitive"):
        try:
            sfm.RemoveSpatialFieldPrimitive(sfp_id)
            return True
        except Exception as ex:
            mlogger.debug("Could not remove AVF primitive {}: {}".format(sfp_id, ex))
            return False


def get_or_create_marker_display_style(doc, style_name, show_legend=False):
    """Get an existing marker-style AnalysisDisplayStyle, or create one.

    Creates a style that shows values as text markers (no color gradient),
    which is a good default for discrete/inspectable values. An existing
    style with this name is returned unchanged, whatever its type.

    The marker size keeps the API default. To change it, edit the returned
    style inside a transaction::

        settings = style.GetMarkersAndTextSettings()
        settings.MarkerSize = 2.0 / 304.8
        style.SetMarkersAndTextSettings(settings)

    ``MarkerSize`` is a length on paper in feet, so the line above sets
    2 mm.

    Args:
        doc (DB.Document): Document to search/create in.
        style_name (str): Name of the display style.
        show_legend (bool, optional): Show the AVF legend in views using
            this style. Defaults to False.

    Returns:
        DB.Analysis.AnalysisDisplayStyle: The existing or newly created
            style.
    """
    existing = query.get_elements_by_class(DB.Analysis.AnalysisDisplayStyle, doc=doc)
    for style in existing:
        if style.Name == style_name:
            return style

    with Transaction("Create Analysis Display Style"):
        color_settings = DB.Analysis.AnalysisDisplayColorSettings()
        legend_settings = DB.Analysis.AnalysisDisplayLegendSettings()
        legend_settings.ShowLegend = show_legend

        marker_text_settings = DB.Analysis.AnalysisDisplayMarkersAndTextSettings()
        marker_text_settings.TextLabelType = (
            DB.Analysis.AnalysisDisplayStyleMarkerTextLabelType.ShowAll
        )

        style = DB.Analysis.AnalysisDisplayStyle.CreateAnalysisDisplayStyle(
            doc, style_name, marker_text_settings, color_settings, legend_settings
        )

    return style


def get_or_create_colored_surface_display_style(
    doc,
    style_name,
    min_color=(200, 0, 200),
    max_color=(255, 205, 0),
    show_legend=True,
    show_grid_lines=True,
    number_of_steps=10,
    rounding=0.05,
):
    """Get an existing colored-surface AnalysisDisplayStyle, or create one.

    Creates a gradient/heatmap style, generally a better fit than
    ``get_or_create_marker_display_style`` for continuous or comparative
    values (e.g. KPI heatmaps) rather than discrete inspectable ones.

    Args:
        doc (DB.Document): Document to search/create in.
        style_name (str): Name of the display style.
        min_color (tuple[int, int, int], optional): RGB for the low end
            of the gradient. Defaults to purple.
        max_color (tuple[int, int, int], optional): RGB for the high end
            of the gradient. Defaults to orange.
        show_legend (bool, optional): Show the AVF legend. Defaults to
            True (usually what you want for a gradient, unlike markers).
        show_grid_lines (bool, optional): Show grid lines on the colored
            surface. Defaults to True.
        number_of_steps (int, optional): Number of discrete color steps
            in the legend/gradient. Defaults to 10.
        rounding (float, optional): Legend value rounding. Defaults to 0.05.

    Returns:
        DB.Analysis.AnalysisDisplayStyle: The existing or newly created
            style.
    """
    existing = query.get_elements_by_class(DB.Analysis.AnalysisDisplayStyle, doc=doc)
    for style in existing:
        if style.Name == style_name:
            return style

    with Transaction("Create Analysis Display Style"):
        surface_settings = DB.Analysis.AnalysisDisplayColoredSurfaceSettings()
        surface_settings.ShowGridLines = show_grid_lines

        color_settings = DB.Analysis.AnalysisDisplayColorSettings()
        color_settings.MinColor = DB.Color(*min_color)
        color_settings.MaxColor = DB.Color(*max_color)

        legend_settings = DB.Analysis.AnalysisDisplayLegendSettings()
        legend_settings.ShowLegend = show_legend
        legend_settings.NumberOfSteps = number_of_steps
        legend_settings.Rounding = rounding

        style = DB.Analysis.AnalysisDisplayStyle.CreateAnalysisDisplayStyle(
            doc, style_name, surface_settings, color_settings, legend_settings
        )

    return style


def display_avf_values_at_points(
    point_value_pairs,
    view,
    schema_name="pyRevitAVF",
    schema_desc="AVF values from pyRevit",
    unit="Value",
    visible=True,
    max_points_per_primitive=500,
):
    """Display values at arbitrary XYZ points, not tied to any element.

    Useful for point-cloud style overlays (e.g. a sampled grid) where
    there's no host element/face to anchor the value to. Per Revit's own
    guidance, points are chunked into multiple primitives of at most
    ``max_points_per_primitive`` points each, rather than one giant
    primitive, for performance.

    Args:
        point_value_pairs (list[tuple[DB.XYZ, float]]): Points and their
            values.
        view (DB.View): View to display values in.
        schema_name (str, optional): AVF schema name.
        schema_desc (str, optional): AVF schema description.
        unit (str or list[tuple[str, float]], optional): See
            ``_get_or_create_schema``.
        visible (bool, optional): Whether the schema is visible. Defaults
            to True.
        max_points_per_primitive (int, optional): Chunk size. Defaults to
            500, per Revit's documented recommendation.

    Returns:
        list[int]: The primitive ids created (one per chunk).
    """
    if max_points_per_primitive <= 0:
        raise PyRevitException("max_points_per_primitive must be > 0")

    sfp_ids = []

    with Transaction("Display AVF Point Values"):
        sfm = _get_or_create_sfm(view)
        schema_id = _get_or_create_schema(
            sfm, schema_name, schema_desc, unit, visible=visible
        )

        for start in range(0, len(point_value_pairs), max_points_per_primitive):
            chunk = point_value_pairs[start : start + max_points_per_primitive]

            xyz_list = List[DB.XYZ]()
            val_list = List[DB.Analysis.ValueAtPoint]()
            for point, value in chunk:
                xyz_list.Add(point)
                val_double_list = List[System.Double]()
                val_double_list.Add(System.Double(value))
                val_list.Add(DB.Analysis.ValueAtPoint(val_double_list))

            domain_pts = DB.Analysis.FieldDomainPointsByXYZ(xyz_list)
            vals = DB.Analysis.FieldValues(val_list)

            sfp_id = sfm.AddSpatialFieldPrimitive()
            sfm.UpdateSpatialFieldPrimitive(sfp_id, domain_pts, vals, schema_id)
            sfp_ids.append(sfp_id)

    return sfp_ids
