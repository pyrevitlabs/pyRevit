# -*- coding: utf-8 -*-
"""Scene data for the Section Box Navigator 3D preview.

Describes the model, levels, grids, scope boxes and the section or crop box
as JSON-ready dictionaries for the preview page.

Invariant:
    Every coordinate sent to the page is model feet relative to the scene
    ``origin`` chosen once per preview session, so 32-bit floats stay precise
    on models far from the internal origin. Box transforms carry only their
    origin relative to it; basis vectors and the local ``min``/``max`` are
    unchanged.
"""

import time

from pyrevit import DB
from pyrevit.compat import get_elementid_value_func
from pyrevit.revit import units
from scene3d.meshing import (
    FloatArray,
    IntArray,
    element_bbox,
    relative,
    tessellate_element,
    union_bbox,
    vector,
)

from sectionbox_geometry import get_box_info, get_crop_edit_blocker
from sectionbox_sources import get_scope_boxes, scope_box_to_bounding_box
from sectionbox_utils import get_view_range_and_crop, is_2d_view

get_elementid_value = get_elementid_value_func()

MAX_ELEMENT_POINTS = 20000
MAX_TOTAL_POINTS = 3000000
NON_GEOMETRY_CATEGORIES = {
    "Sheets": -2003100,
    "Sketch Lines": -2000045,
    "Lines": -2000051,
    "Detail Items": -2002000,
    "Raster Images": -2000560,
    "Legend Components": -2000576,
    "Cameras": -2000500,
    "RVT Links": -2001352,
    "Sun Path": -2009609,
    "Materials": -2000700,
    "Material Assets": -2000924,
    "Project Information": -2003101,
    "Internal Origin": -2000977,
    "Project Base Point": -2001271,
    "Survey Point": -2001272,
    "Primary Contours": -2001342,
    "HVAC Zones": -2008107,
    "Area Based Load Type": -2001019,
    "Pipe Segments": -2008163,
    "Divisions": -2000291,
    "Areas": -2003200,
    "Area Boundary": -2000079,
    "Room Separation": -2000066,
    "Space Separation": -2000831,
    "Scope Boxes": -2000200,
    "Section Boxes": -2000301,
}
HIDDEN_BY_DEFAULT_CATEGORIES = {
    "Rooms": -2000160,
    "Spaces": -2003600,
    "Parts": -2000269,
}
_EXCLUDED_CATEGORY_IDS = frozenset(NON_GEOMETRY_CATEGORIES.values())
_HIDDEN_BY_DEFAULT_IDS = frozenset(HIDDEN_BY_DEFAULT_CATEGORIES.values())


def _category_id(element):
    return int(get_elementid_value(element.Category.Id))


def _is_candidate(element):
    category = element.Category
    if category is None or category.CategoryType != DB.CategoryType.Model:
        return False
    if isinstance(element, DB.Group):
        return False
    if element.OwnerViewId != DB.ElementId.InvalidElementId:
        return False
    return _category_id(element) not in _EXCLUDED_CATEGORY_IDS


def _model_elements(doc):
    collector = DB.FilteredElementCollector(doc).WhereElementIsNotElementType()
    return [element for element in collector if _is_candidate(element)]


class _Entry(object):
    __slots__ = ("element", "bbox", "transform", "group", "source", "size")

    def __init__(self, element, bbox, transform, group, source):
        self.element = element
        self.bbox = bbox
        self.transform = transform
        self.group = group
        self.source = source
        self.size = (bbox.Max - bbox.Min).GetLength()


class ModelStream(object):
    """Tessellates the model in time-sliced chunks, largest elements first.

    Args:
        doc (DB.Document): host document.
        origin (DB.XYZ): scene origin.
        include_links (bool): also stream the geometry of loaded Revit links,
            grouped one entry per link as "Link: <title>".
        links_only (bool): stream only the links, for a page that already
            holds the host model.

    Elements that are not 3D geometry are left out: view-specific elements,
    the categories in ``NON_GEOMETRY_CATEGORIES`` and any element without
    geometry. Rooms, spaces and parts are streamed for the host model flagged
    ``hidden`` (the page starts with their category unticked) and skipped in
    links, whose elements share one group per link.

    Invariant:
        Chunks are independent: the page appends meshes as they arrive. An
        element's page key is ``source`` (0 for the host, then link order) and
        its id, because link element ids can equal host ids.
    """

    def __init__(self, doc, origin, include_links, links_only=False):
        self.doc = doc
        self.origin = origin
        self.include_links = include_links
        self.links_only = links_only
        self._entries = None
        self._cursor = 0
        self._points = 0

    @property
    def done(self):
        """True once every prepared element has been streamed."""
        return self._entries is not None and self._cursor >= len(self._entries)

    def _sources(self):
        sources = [(self.doc, None, None)]
        if self.include_links:
            instances = DB.FilteredElementCollector(self.doc).OfClass(
                DB.RevitLinkInstance
            )
            for instance in instances:
                link_doc = instance.GetLinkDocument()
                if link_doc is not None:
                    sources.append(
                        (link_doc, instance.GetTotalTransform(), link_doc.Title)
                    )
        return sources

    def _prepare(self):
        entries = []
        for source, (doc, transform, title) in enumerate(self._sources()):
            if self.links_only and source == 0:
                continue
            group = None if title is None else "Link: {}".format(title)
            for element in _model_elements(doc):
                if group and _category_id(element) in _HIDDEN_BY_DEFAULT_IDS:
                    continue
                bbox = element_bbox(element)
                if bbox is not None:
                    entries.append(_Entry(element, bbox, transform, group, source))
        entries.sort(key=lambda entry: (entry.source, -entry.size))
        self._entries = entries

    @property
    def total(self):
        """Number of elements to stream, available after the first chunk."""
        return len(self._entries or ())

    def next_chunk(self, seconds):
        """Tessellate for about ``seconds`` and return the chunk, or None when done.

        Returns:
            (dict | None): ``{"meshes": [...], "progress": [done, total]}``
            ready for :func:`scene3d.meshing.scene_to_json`.
        """
        if self._entries is None:
            self._prepare()
        if self._cursor >= len(self._entries):
            return None
        deadline = time.time() + seconds
        meshes = []
        while self._cursor < len(self._entries) and time.time() < deadline:
            entry = self._entries[self._cursor]
            self._cursor += 1
            budget = min(MAX_ELEMENT_POINTS, max(MAX_TOTAL_POINTS - self._points, 0))
            builder, approx = tessellate_element(
                entry.element,
                entry.bbox,
                self.origin,
                budget,
                edges=False,
                transform=entry.transform,
                box_when_empty=False,
            )
            if not builder.indices:
                continue
            self._points += builder.point_count
            category = entry.element.Category
            meshes.append(
                {
                    "id": int(get_elementid_value(entry.element.Id)),
                    "source": entry.source,
                    "group": entry.group or category.Name,
                    "hidden": entry.group is None
                    and _category_id(entry.element) in _HIDDEN_BY_DEFAULT_IDS,
                    "approx": approx,
                    "positions": FloatArray(builder.positions),
                    "indices": IntArray(builder.indices),
                }
            )
        return {"meshes": meshes, "progress": [self._cursor, len(self._entries)]}


def scene_origin(doc, box):
    """Return the scene origin: the center of the model's bounds, else of ``box``."""
    bounds = union_bbox(
        [element_bbox(element) for element in _model_elements(doc)] + [box]
    )
    if bounds is None:
        return DB.XYZ.Zero
    return (bounds.Min + bounds.Max) * 0.5


def box_payload(box, origin):
    """Describe a ``DB.BoundingBoxXYZ`` for the page, relative to ``origin``."""
    transform = box.Transform
    return {
        "origin": relative(transform.Origin, origin),
        "bx": vector(transform.BasisX),
        "by": vector(transform.BasisY),
        "bz": vector(transform.BasisZ),
        "min": vector(box.Min),
        "max": vector(box.Max),
    }


def box_from_payload(payload, origin, template=None):
    """Build a ``DB.BoundingBoxXYZ`` from a page box, the inverse of :func:`box_payload`.

    Args:
        payload (dict): box as described by :func:`box_payload`.
        origin (DB.XYZ): the scene origin the payload is relative to.
        template (DB.BoundingBoxXYZ | None): when given, only its X and Y
            extents are replaced and Z is kept, for crop boxes whose Z range
            is not edited.
    """
    transform = DB.Transform.Identity
    transform.Origin = DB.XYZ(
        origin.X + payload["origin"][0],
        origin.Y + payload["origin"][1],
        origin.Z + payload["origin"][2],
    )
    transform.BasisX = DB.XYZ(*payload["bx"])
    transform.BasisY = DB.XYZ(*payload["by"])
    transform.BasisZ = DB.XYZ(*payload["bz"])
    box = DB.BoundingBoxXYZ()
    box.Transform = transform
    low, high = payload["min"], payload["max"]
    if template is None:
        box.Min = DB.XYZ(*low)
        box.Max = DB.XYZ(*high)
    else:
        box.Min = DB.XYZ(low[0], low[1], template.Min.Z)
        box.Max = DB.XYZ(high[0], high[1], template.Max.Z)
    return box


def _plan_display_box(view, crop):
    """Return the crop box with its Z range replaced by the view range's extent."""
    ranges = get_view_range_and_crop(view, view.Document)
    top, bottom = ranges["top_elevation"], ranges["bottom_elevation"]
    if top is None or bottom is None:
        return crop
    transform = crop.Transform
    z_axis = transform.BasisZ.Z
    if abs(z_axis) < 1e-9:
        return crop
    low = (bottom - transform.Origin.Z) / z_axis
    high = (top - transform.Origin.Z) / z_axis
    shown = DB.BoundingBoxXYZ()
    shown.Transform = transform
    shown.Min = DB.XYZ(crop.Min.X, crop.Min.Y, min(low, high))
    shown.Max = DB.XYZ(crop.Max.X, crop.Max.Y, max(low, high))
    return shown


def view_payload(view, datafilename, origin):
    """Describe the active view's box for the page.

    Returns:
        (dict): ``kind`` ("3d" or "crop"), ``name``, ``box`` (None when the
        view has no box), ``editable`` (face ids the page may drag: ``x0``,
        ``x1``, ``y0``, ``y1``, ``z0``, ``z1``) and ``blocker`` (why a crop
        cannot be edited, or None).
    """
    is_3d = isinstance(view, DB.View3D)
    info = get_box_info(view, datafilename) if is_3d or is_2d_view(view) else None
    payload = {
        "kind": "3d" if is_3d else "crop",
        "name": view.Name,
        "box": None,
        "editable": [],
        "blocker": None,
        "camera": None,
    }
    if info is None:
        return payload
    box = info["box"]
    if is_3d:
        payload["editable"] = ["x0", "x1", "y0", "y1", "z0", "z1"]
        payload["active"] = bool(view.IsSectionBoxActive)
        try:
            orientation = view.GetOrientation()
            payload["camera"] = {
                "forward": vector(orientation.ForwardDirection),
                "up": vector(orientation.UpDirection),
                "eye": relative(orientation.EyePosition, origin),
                "perspective": bool(view.IsPerspective),
            }
        except Exception:
            payload["camera"] = None
    else:
        payload["blocker"] = get_crop_edit_blocker(view)
        payload["editable"] = [] if payload["blocker"] else ["x0", "x1", "y0", "y1"]
        if isinstance(view, DB.ViewPlan):
            box = _plan_display_box(view, box)
    payload["box"] = box_payload(box, origin)
    return payload


def levels_payload(levels, origin):
    """Describe levels as ``{name, z, elevation, link}`` entries.

    ``z`` is relative to ``origin``, ``elevation`` is the project elevation
    shown to the user. A linked level with the same name and elevation as one
    already listed is left out.
    """
    entries = []
    seen = set()
    for level in levels:
        key = (level.Name, round(level.ProjectElevation, 4))
        if key in seen:
            continue
        seen.add(key)
        entries.append(
            {
                "name": level.Name,
                "z": level.ProjectElevation - origin.Z,
                "elevation": level.ProjectElevation,
                "link": hasattr(level, "SourceLink"),
            }
        )
    return entries


def grids_payload(grids, origin):
    """Describe grids as ``{name, link, segs}``, segments being ``[x1, y1, x2, y2]``."""
    entries = []
    for grid in grids:
        linked = hasattr(grid, "SourceLink")
        curve = grid.Curve
        if curve is None:
            continue
        points = list(curve.Tessellate())
        segments = [
            [
                start.X - origin.X,
                start.Y - origin.Y,
                end.X - origin.X,
                end.Y - origin.Y,
            ]
            for start, end in zip(points, points[1:])
        ]
        entries.append(
            {
                "name": grid.Element.Name if linked else grid.Name,
                "link": linked,
                "segs": segments,
            }
        )
    return entries


def scope_boxes_payload(doc, origin):
    """Describe the document's scope boxes as ``{id, name, box}`` entries."""
    entries = []
    for scope_box in get_scope_boxes(doc):
        box = scope_box_to_bounding_box(scope_box)
        if box is not None:
            entries.append(
                {
                    "id": int(get_elementid_value(scope_box.Id)),
                    "name": scope_box.Name,
                    "box": box_payload(box, origin),
                }
            )
    return entries


def units_payload(doc):
    """Describe the project length unit: ``factor`` (feet to unit), ``symbol``, ``decimals``."""
    length_unit, _, _, symbol = units.get_unit_info(DB.SpecTypeId.Length, doc)
    factor = DB.UnitUtils.Convert(1.0, DB.UnitTypeId.Feet, length_unit)
    if factor >= 100:
        decimals = 0
    elif factor < 1:
        decimals = 3
    else:
        decimals = 2
    return {"factor": factor, "symbol": symbol or "", "decimals": decimals}
