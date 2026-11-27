# -*- coding: utf-8 -*-
"""Analysis Visualization Framework (AVF) helpers.

Utilities for displaying arbitrary numeric values on elements in a view,
using Revit's SpatialFieldManager / AVF. Useful for heatmaps, KPI overlays,
QA/QC markers, or any "paint a number onto elements" workflow.

Typical usage::

    from pyrevit import revit
    from pyrevit.revit import avf

    report = avf.show_values(
        revit.active_view,
        {wall1: 12.5, wall2.Id: 44.0, 316542: 7},
        name="Fire rating",
        unit="min",
    )
    avf.show_values(
        revit.active_view, {wall1: 90, wall2: None}, "Fire rating", keep_others=True
    )
    avf.clear_values(revit.active_view, "Fire rating")

Use :func:`show_values` and :func:`clear_values`. By default each call makes
the view show exactly the values passed under ``name``. To add, change or
remove single values without knowing the others, pass ``keep_others=True``;
None as a value removes it. Both assign a display style, refresh the view and
report what happened to every element. Other names, and results of other
tools, are left alone.

The remaining functions are lower level building blocks. They add values
without replacing earlier ones, and their caller keeps the primitive ids,
assigns a display style and refreshes the view.

Notes / known limitations:
    - Nothing is drawn without an AnalysisDisplayStyle on the view
      (``View.AnalysisDisplayStyleId``). Only :func:`show_values` assigns
      one.
    - Marker size belongs to the display style, not to the values:
      ``AnalysisDisplayMarkersAndTextSettings.MarkerSize`` is a length on
      paper in Revit internal units (feet). A marker spans about
      ``MarkerSize * view.Scale`` feet in the model. The API default is
      1/96 ft (about 3.2 mm on paper). :func:`show_values` takes
      millimetres as ``marker_size_mm``.
    - Values are numbers shown as given. ``unit`` is a label, nothing is
      converted from Revit internal units.
    - Values are anchored to faces only in orthographic 3D views without an
      active section box, for elements visible in that view. Everywhere else
      they are placed at the element's bounding-box center, which text
      markers draw but a colored-surface style cannot paint.
    - Face selection uses the largest planar-or-curved face turned toward
      the viewer. It is sampled at the point of that face nearest to the
      middle of its UV bounding box, which is an approximation for strongly
      curved faces (cylinders, etc.).
    - AVF results are NOT saved with the document: they live only for the
      current session. What IS saved with the model is the
      AnalysisDisplayStyle and its assignment to a view.
    - Rolling a transaction group back does not reliably remove AVF
      results. A rolled back script or a dry run can leave values behind,
      so remove them with :func:`clear_values`.
    - Revit cannot list a view's primitives. :func:`show_values` remembers
      its own in the Revit process, shared by all engines.
    - The write functions open their own transaction, which becomes a
      SubTransaction when one is already open on the view's document.
"""

import json
import math

from pyrevit import DB, HOST_APP
from pyrevit import PyRevitException
from pyrevit.revit import Transaction, query
from pyrevit.framework import AppDomain, List, System
from pyrevit.coreutils.logger import get_logger
from pyrevit.compat import get_elementid_value_func
from pyrevit.compat import get_elementid_from_value_func

get_elementid_value = get_elementid_value_func()
get_elementid_from_value = get_elementid_from_value_func()

mlogger = get_logger(__name__)

_FACING_TOLERANCE = 1e-6
_SAMPLE_STEPS = 8
_STATE_SLOT = "PYREVIT_AVF_SHOWN_VALUES"
_MEASUREMENT_NAME = "Value"
_MILLIMETRES_PER_FOOT = 304.8
_STYLE_KINDS = {"marker": "Marker", "colored": "Colored Surface"}
_PROHIBITED_NAME_CHARACTERS = "\\:{}[]|;<>?`~"

__all__ = (
    "show_values",
    "clear_values",
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
        which no ``try``/``except`` can catch. One direction does not tell
        which faces a perspective view shows.
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


def _get_sample_uv(face):
    center = _get_uv_center(face)
    if face.IsInside(center):
        return center
    bbox = face.GetBoundingBox()
    fractions = [step / float(_SAMPLE_STEPS) for step in range(1, _SAMPLE_STEPS)]
    for u_fraction, v_fraction in sorted(
        ((u, v) for u in fractions for v in fractions),
        key=lambda pair: (pair[0] - 0.5) ** 2 + (pair[1] - 0.5) ** 2,
    ):
        candidate = DB.UV(
            bbox.Min.U + (bbox.Max.U - bbox.Min.U) * u_fraction,
            bbox.Min.V + (bbox.Max.V - bbox.Min.V) * v_fraction,
        )
        if face.IsInside(candidate):
            return candidate
    return None


def _can_anchor_to_faces(view):
    return (
        isinstance(view, DB.View3D)
        and not view.IsPerspective
        and not view.IsSectionBoxActive
    )


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
    return set(int(get_elementid_value(element_id)) for element_id in visible_ids)


def _get_face_anchor(element, view):
    detail_level = view.DetailLevel
    if detail_level == DB.ViewDetailLevel.Undefined:
        detail_level = DB.ViewDetailLevel.Medium
    face = get_face_facing_direction(
        element, view.ViewDirection, detail_level=detail_level
    )
    if face is None or face.Reference is None:
        return None
    sample_uv = _get_sample_uv(face)
    if sample_uv is None:
        return None
    return face.Reference, sample_uv


def _get_center(element, view):
    bbox = element.get_BoundingBox(view)
    if bbox is None:
        return None
    return (bbox.Min + bbox.Max) / 2.0


def _resolve_anchors(elements_and_values, view, face_candidate_ids):
    """Read every element's face anchor and center before anything is added.

    Adding a primitive makes the next geometry or view query regenerate,
    which can take seconds, so no query may run between two primitives.
    """
    anchors = []
    for element, value in elements_and_values:
        elem_id = int(get_elementid_value(element.Id))
        face_anchor = center = None
        if elem_id in face_candidate_ids:
            try:
                face_anchor = _get_face_anchor(element, view)
            except Exception as ex:
                mlogger.debug(
                    "Could not read a face of element ID {}: {}".format(elem_id, ex)
                )
        try:
            center = _get_center(element, view)
        except Exception as ex:
            mlogger.exception("Error reading element ID {}: {}".format(elem_id, ex))
        anchors.append((elem_id, value, face_anchor, center))
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


def _add_anchored_value(sfm, schema_id, value, face_anchor, center):
    """Add one value and return ``(primitive id, True if anchored to a face)``."""
    primitive = _add_face_primitive(sfm, *face_anchor) if face_anchor else None
    on_face = primitive is not None
    if primitive is None:
        if center is None:
            raise PyRevitException("not visible in the view (no bounding box)")
        primitive = _add_point_primitive(sfm, center)
    sfp_id, domain_points = primitive
    try:
        sfm.UpdateSpatialFieldPrimitive(
            sfp_id, domain_points, _make_field_values(value), schema_id
        )
    except Exception:
        sfm.RemoveSpatialFieldPrimitive(sfp_id)
        raise
    return sfp_id, on_face


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
        if number_of_measurements == 1:
            measurement_names = List[System.String]()
            measurement_names.Add(_MEASUREMENT_NAME)
            sfm.SetMeasurementNames(measurement_names)
    return sfm


def _find_schema_id(sfm, schema_name):
    for sid in sfm.GetRegisteredResults():
        if sfm.GetResultSchema(sid).Name == schema_name:
            return sid
    return None


def _get_unit_pairs(units):
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
    return unit_pairs


def _build_schema(schema_name, schema_desc, unit_pairs, visible):
    unit_name_list = List[System.String]()
    unit_multiplier_list = List[System.Double]()
    for unit_name, multiplier in unit_pairs:
        unit_name_list.Add(unit_name)
        unit_multiplier_list.Add(System.Double(multiplier))
    schema = DB.Analysis.AnalysisResultSchema(schema_name, schema_desc)
    schema.SetUnits(unit_name_list, unit_multiplier_list)
    schema.IsVisible = visible
    return schema


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
            ``UpdateSpatialFieldPrimitive``. An existing schema keeps its
            units and description.
    """
    schema_id = _find_schema_id(sfm, schema_name)
    if schema_id is not None:
        return schema_id
    return sfm.RegisterResult(
        _build_schema(schema_name, schema_desc, _get_unit_pairs(units), visible)
    )


def _load_state():
    stored = AppDomain.CurrentDomain.GetData(_STATE_SLOT)
    return json.loads(stored) if stored else {}


def _get_state_key(view, name):
    return "{}|{}|{}".format(
        view.Document.GetHashCode(), int(get_elementid_value(view.Id)), name
    )


def _get_tracked_entry(sfm, view, name):
    """Return what is remembered about *name* in *view*, or None if unknown.

    Primitive ids are only trusted while the result they were added to is
    still registered at the same index. Revit does not reuse indices within
    a SpatialFieldManager, so clearing it invalidates what was remembered.
    """
    if sfm is None:
        return None
    entry = _load_state().get(_get_state_key(view, name))
    if not entry:
        return None
    registered = [int(sid) for sid in sfm.GetRegisteredResults()]
    if entry["result"] not in registered:
        return None
    if sfm.GetResultSchema(entry["result"]).Name != name:
        return None
    return entry


def _remember_entry(view, name, entry):
    state = _load_state()
    state[_get_state_key(view, name)] = entry
    AppDomain.CurrentDomain.SetData(_STATE_SLOT, json.dumps(state, ensure_ascii=False))


def _mark_result_shared(sfm, view, name):
    """Stop treating the settings of a result as owned by :func:`show_values`.

    Called by the lower level writers, because values they add to a result
    mean something only with the unit it has at that time.
    """
    entry = _get_tracked_entry(sfm, view, name)
    if entry and not entry["borrowed"]:
        entry["borrowed"] = True
        _remember_entry(view, name, entry)


def _remove_primitives(sfm, primitive_ids):
    removed = 0
    for sfp_id in primitive_ids:
        try:
            sfm.RemoveSpatialFieldPrimitive(sfp_id)
            removed += 1
        except Exception as ex:
            mlogger.debug("AVF primitive {} is already gone: {}".format(sfp_id, ex))
    return removed


def _read_values(values, allow_removal):
    pairs = values.items() if hasattr(values, "items") else values
    numbers = []
    for key, value in pairs:
        if value is None:
            if not allow_removal:
                raise PyRevitException(
                    "None removes a value and needs keep_others=True"
                )
            numbers.append((key, None))
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            raise PyRevitException("Not a number: {!r}".format(value))
        if math.isnan(number) or math.isinf(number):
            raise PyRevitException("Values must be finite. Got: {!r}".format(value))
        numbers.append((key, number))
    return numbers


def _find_elements(numbers, doc):
    """Sort ``(key, value)`` pairs by what has to happen to each element.

    Returns:
        tuple: ``(element, number)`` pairs to show, element ids whose value
            is to be removed (they need not exist anymore) and failures by id.
    """
    found, removals, failed, seen = {}, [], {}, set()
    for key, number in numbers:
        element = None
        if hasattr(key, "Id"):
            elem_id = int(get_elementid_value(key.Id))
            if not key.Document.Equals(doc):
                failed[elem_id] = "belongs to another document than the view"
                continue
            element = key
        else:
            element_id = (
                key if isinstance(key, DB.ElementId) else get_elementid_from_value(key)
            )
            elem_id = int(get_elementid_value(element_id))
            if number is not None:
                element = doc.GetElement(element_id)
        if elem_id in seen:
            raise PyRevitException(
                "Element ID {} was passed more than once".format(elem_id)
            )
        seen.add(elem_id)
        if number is None:
            removals.append(elem_id)
        elif element is None:
            failed[elem_id] = "no element with this id in the view's document"
        else:
            found[elem_id] = (element, number)
    return [found[elem_id] for elem_id in sorted(found)], sorted(removals), failed


def _normalize_unit_pairs(unit):
    return [[unit_name, float(factor)] for unit_name, factor in _get_unit_pairs(unit)]


def _read_unit_pairs(schema):
    return [
        [schema.GetUnitsName(index), float(schema.GetUnitsMultiplier(index))]
        for index in range(schema.GetNumberOfUnits())
    ]


def _find_borrowed_schema(sfm, name, previous):
    """Return the result called *name* if its settings are not ours to change.

    That is a result :func:`show_values` did not register itself. It can hold
    values added some other way, whose numbers mean something only with its
    current unit.
    """
    if sfm is None or (previous is not None and not previous["borrowed"]):
        return None
    schema_id = _find_schema_id(sfm, name)
    return None if schema_id is None else sfm.GetResultSchema(schema_id)


def _check_borrowed_settings(schema, unit, description):
    unit_differs = unit is not None and _normalize_unit_pairs(unit) != _read_unit_pairs(
        schema
    )
    if unit_differs or (description is not None and description != schema.Description):
        raise PyRevitException(
            "The result '{}' was not created by show_values, so its unit and "
            "description cannot change: it can hold other values. Use another "
            "name, or clear_avf_results to remove it.".format(schema.Name)
        )


def _choose_unit_pairs(unit, retained, passed_ids):
    """Return the unit pairs to use and whether they differ from *retained*."""
    if retained is None:
        return _normalize_unit_pairs("Value" if unit is None else unit), False
    if unit is None:
        return retained["unit"], False
    unit_pairs = _normalize_unit_pairs(unit)
    if unit_pairs == retained["unit"]:
        return unit_pairs, False
    if any(int(elem_id) not in passed_ids for elem_id in retained["values"]):
        raise PyRevitException(
            "One unit applies to all values of a name. To change it while keeping "
            "others, pass every one of them, or use keep_others=False."
        )
    return unit_pairs, True


def _get_style_name(kind, name):
    safe_name = "".join(
        "_" if char in _PROHIBITED_NAME_CHARACTERS else char for char in name
    )
    return "pyRevit AVF {} - {}".format(_STYLE_KINDS[kind], safe_name)


def _prepare_style(doc, name, style, marker_size_mm):
    if style is None:
        return None
    if style == "colored":
        return get_or_create_colored_surface_display_style(
            doc, _get_style_name(style, name)
        )
    if style != "marker":
        return style
    marker_style = get_or_create_marker_display_style(doc, _get_style_name(style, name))
    if marker_size_mm is not None:
        settings = marker_style.GetMarkersAndTextSettings()
        settings.MarkerSize = marker_size_mm / _MILLIMETRES_PER_FOOT
        with Transaction("Set AVF Marker Size", doc=doc):
            marker_style.SetMarkersAndTextSettings(settings)
    return marker_style


def _check_view(view, name):
    if not name:
        raise PyRevitException("name must be a non-empty string")
    if not view.AllowsAnalysisDisplay():
        raise PyRevitException(
            "View '{}' cannot display analysis results".format(view.Name)
        )


def _choose_style(style, retained, doc):
    if not hasattr(style, "lower") or style != "auto":
        return style
    if retained is None:
        return "marker"
    stored = retained["style"]
    if stored is None or hasattr(stored, "lower"):
        return stored
    return doc.GetElement(get_elementid_from_value(stored))


def _describe_style(style):
    if style is None or hasattr(style, "lower"):
        return style
    return int(get_elementid_value(style.Id))


def _check_style(view, style, marker_size_mm):
    if style == "colored" and not _can_anchor_to_faces(view):
        raise PyRevitException(
            "A colored surface needs faces, which are only used in an orthographic "
            "3D view without an active section box. Use such a view or "
            "style='marker'."
        )
    if hasattr(style, "lower") and style not in _STYLE_KINDS:
        raise PyRevitException(
            "style must be 'auto', 'marker', 'colored', an AnalysisDisplayStyle "
            "or None. "
            "Got: {!r}".format(style)
        )
    if marker_size_mm is not None and (style != "marker" or marker_size_mm <= 0):
        raise PyRevitException(
            "marker_size_mm must be positive and needs style='marker'"
        )


def _refresh_if_active(view):
    uidoc = HOST_APP.uidoc
    if not uidoc or not uidoc.Document.Equals(view.Document):
        return
    if uidoc.ActiveView and uidoc.ActiveView.Id == view.Id:
        uidoc.RefreshActiveView()


def show_values(
    view,
    values,
    name="pyRevitAVF",
    unit=None,
    style="auto",
    marker_size_mm=None,
    description=None,
    keep_others=False,
):
    """Show or update numbers on elements in a view: markers or a heatmap.

    By default the view then shows exactly *values* under the result called
    *name*: calling it again replaces everything the earlier call showed
    under that name. With ``keep_others=True`` only the elements passed are
    added, updated or removed and all other values of *name* stay. Both ways
    are safe to repeat. Values under other names always stay.

    Args:
        view (DB.View): View to draw in. Its document must be modifiable.
        values (dict or list[tuple]): Element -> number. A key is a
            ``DB.Element``, a ``DB.ElementId`` or an element id as int. With
            ``keep_others``, None instead of a number removes that element's
            value, also if the element no longer exists. Without it, an
            empty collection removes all values of *name*.
        name (str, optional): Identifies this set of values. It is also the
            result name in the legend.
        unit (str or list[tuple[str, float]], optional): Unit label, or
            ``(unit_name, multiplier)`` pairs the viewer can switch
            between. Numbers are not converted from Revit internal units.
            None means ``"Value"``, or the current unit when other values
            are kept. One unit applies to all values of a name. A result of
            this name that :func:`show_values` did not create keeps its unit
            and description, and asking for different ones raises.
        style (str or DB.Analysis.AnalysisDisplayStyle, optional):
            ``"marker"`` for a dot with the number, ``"colored"`` for a
            painted surface (orthographic 3D view without a section box, not
            wireframe), an existing style, or None to keep the view's current
            style. ``"auto"`` means ``"marker"``, or what the last call for
            this name used when other values are kept (the view's style
            stays if that one was deleted since). A view has one style,
            so the last call decides how all names look.
        marker_size_mm (float, optional): Marker size on paper in
            millimetres, for markers. None keeps the size the style has,
            about 3.2 mm for a new one.
        description (str, optional): Text under the legend. None means
            *name*, or the current text when other values are kept.
        keep_others (bool, optional): Keep the values of *name* on elements
            that are not in *values*. Defaults to False.

    Returns:
        dict: ``view_id``, ``name``, ``style`` (name of the assigned style or
            None), ``shown`` (element ids added or updated by this call),
            ``on_faces`` (those of them anchored to a face; only these can be
            painted by a colored surface), ``present`` (all element ids that
            now have a value under *name*), ``failed`` (element id ->
            reason; with ``keep_others`` such an element keeps its earlier
            value unless the unit changed), ``removed`` (number of earlier
            values removed or replaced) and ``untracked_result`` (True when
            *name* already existed but its values were not added through
            this function, so they could not be replaced). All values are
            plain Python types.

    Raises:
        PyRevitException: For a request that cannot work, such as a view
            without analysis display, a colored surface outside a suitable
            3D view, a value that is not a finite number, or a new unit while
            values in the old one are kept. Nothing is changed in that case.
            Also raised if Revit rolled the style change back; the values are
            not rolled back with it.

    Note:
        Assigning the style changes the view and is saved with the model.
        The values themselves are not saved, and rolling back an enclosing
        transaction group does not reliably remove them.
    """
    _check_view(view, name)
    numbers = _read_values(values, keep_others)
    doc = view.Document
    elements_and_values, removals, failed = _find_elements(numbers, doc)
    existing_sfm = DB.Analysis.SpatialFieldManager.GetSpatialFieldManager(view)
    previous = _get_tracked_entry(existing_sfm, view, name)
    borrowed_schema = _find_borrowed_schema(existing_sfm, name, previous)
    retained = previous if keep_others and previous and previous["values"] else None
    style = _choose_style(style, retained, doc)
    _check_style(view, style, marker_size_mm)
    passed_ids = set(removals) | set(failed)
    passed_ids.update(
        int(get_elementid_value(element.Id)) for element, _ in elements_and_values
    )
    if borrowed_schema is not None:
        _check_borrowed_settings(borrowed_schema, unit, description)
        unit_pairs, unit_changed = _read_unit_pairs(borrowed_schema), False
        description = borrowed_schema.Description
    else:
        unit_pairs, unit_changed = _choose_unit_pairs(unit, retained, passed_ids)
        if description is None:
            description = retained["description"] if retained else name
    face_candidate_ids = _get_face_candidate_ids(
        [element for element, _ in elements_and_values], view
    )
    anchors = _resolve_anchors(elements_and_values, view, face_candidate_ids)
    new_schema = (
        _build_schema(name, description, unit_pairs, True)
        if borrowed_schema is None
        else None
    )
    shown, on_faces = [], []
    style_id = style_name = None

    with Transaction("Show AVF Values", doc=doc):
        display_style = _prepare_style(doc, name, style, marker_size_mm)
        if display_style is not None:
            style_id, style_name = display_style.Id, query.get_name(display_style)
            view.AnalysisDisplayStyleId = style_id
        sfm = _get_or_create_sfm(view)
        schema_id = _find_schema_id(sfm, name)
        untracked_result = schema_id is not None and previous is None
        current = dict(previous["values"]) if previous else {}
        removed = 0
        if not keep_others:
            removed = _remove_primitives(sfm, current.values())
            current = {}
        if new_schema is not None:
            if schema_id is None:
                schema_id = sfm.RegisterResult(new_schema)
            else:
                sfm.SetResultSchema(schema_id, new_schema)

        def drop(elem_id):
            key = str(elem_id)
            return _remove_primitives(sfm, [current.pop(key)] if key in current else [])

        for elem_id in removals:
            removed += drop(elem_id)

        for elem_id, value, face_anchor, center in anchors:
            try:
                sfp_id, on_face = _add_anchored_value(
                    sfm, schema_id, value, face_anchor, center
                )
            except Exception as ex:
                failed[elem_id] = str(ex)
                if unit_changed:
                    removed += drop(elem_id)
                continue
            removed += drop(elem_id)
            current[str(elem_id)] = int(sfp_id)
            shown.append(elem_id)
            if on_face:
                on_faces.append(elem_id)

        if unit_changed:
            for elem_id in failed:
                removed += drop(elem_id)

        _remember_entry(
            view,
            name,
            {
                "result": int(schema_id),
                "values": current,
                "unit": unit_pairs,
                "description": description,
                "style": _describe_style(style),
                "borrowed": borrowed_schema is not None,
            },
        )

    if style_id is not None and view.AnalysisDisplayStyleId != style_id:
        raise PyRevitException(
            "Revit did not keep the display style change of this view. AVF "
            "edits are not undone with it, so values may have changed; "
            "clear_values removes those of '{}'.".format(name)
        )
    _refresh_if_active(view)
    return {
        "view_id": int(get_elementid_value(view.Id)),
        "name": name,
        "style": style_name,
        "shown": shown,
        "on_faces": on_faces,
        "present": sorted(int(elem_id) for elem_id in current),
        "failed": failed,
        "removed": removed,
        "untracked_result": untracked_result,
    }


def clear_values(view, name="pyRevitAVF"):
    """Remove numbers shown on elements in a view by :func:`show_values`.

    Other names and results of other tools stay. The display style stays
    assigned to the view.

    Args:
        view (DB.View): View to remove the values from.
        name (str, optional): The name passed to :func:`show_values`.

    Returns:
        int: Number of values removed. 0 when nothing is known under *name*,
            for example because the whole view was cleared meanwhile.
    """
    sfm = DB.Analysis.SpatialFieldManager.GetSpatialFieldManager(view)
    entry = _get_tracked_entry(sfm, view, name)
    if not entry or not entry["values"]:
        return 0
    with Transaction("Clear AVF Values", doc=view.Document):
        removed = _remove_primitives(sfm, entry["values"].values())
        entry["values"] = {}
        _remember_entry(view, name, entry)
    _refresh_if_active(view)
    return removed


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
        with Transaction("Clear AVF Results", doc=view.Document):
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
            turned toward the viewer is used where that is possible: an
            orthographic 3D view without an active section box, an element
            visible in it,
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
    anchors = _resolve_anchors(element_value_dict.items(), view, face_candidate_ids)

    with Transaction("Display AVF Values", doc=view.Document):
        sfm = _get_or_create_sfm(view)
        schema_id = _get_or_create_schema(
            sfm, schema_name, schema_desc, unit, visible=visible
        )
        _mark_result_shared(sfm, view, schema_name)

        for elem_id, value, face_anchor, center in anchors:
            try:
                sfp_id, _ = _add_anchored_value(
                    sfm, schema_id, value, face_anchor, center
                )
                results[elem_id] = (True, sfp_id)
            except Exception as ex:
                mlogger.warning(
                    "Could not display element ID {}: {}".format(elem_id, ex)
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

    with Transaction("Update AVF Values", doc=view.Document):
        sfm = _get_or_create_sfm(view)
        schema_id = _get_or_create_schema(
            sfm, schema_name, schema_desc, unit, visible=visible
        )
        _mark_result_shared(sfm, view, schema_name)

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
    with Transaction("Remove AVF Primitive", doc=view.Document):
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

    with Transaction("Create Analysis Display Style", doc=doc):
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

    with Transaction("Create Analysis Display Style", doc=doc):
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

    with Transaction("Display AVF Point Values", doc=view.Document):
        sfm = _get_or_create_sfm(view)
        schema_id = _get_or_create_schema(
            sfm, schema_name, schema_desc, unit, visible=visible
        )
        _mark_result_shared(sfm, view, schema_name)

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
