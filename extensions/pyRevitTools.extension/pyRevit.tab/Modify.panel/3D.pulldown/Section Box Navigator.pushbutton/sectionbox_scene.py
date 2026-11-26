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
from pyrevit.framework import List
from pyrevit.revit import units
from scene3d.meshing import (
    BOX_POINT_COUNT,
    FloatArray,
    IntArray,
    box_corners,
    element_bbox,
    relative,
    tessellate_element,
    union_bbox,
    vector,
)

from sectionbox_geometry import get_box_info, get_crop_edit_blocker
from sectionbox_guides import drop_repeated_grids, drop_repeated_levels
from sectionbox_sources import get_scope_boxes, scope_box_to_bounding_box
from sectionbox_utils import is_2d_view
from sectionbox_viewrange import is_ceiling_plan, plane_elevations, view_range_payload
from sectionbox_viewrange_rules import BOTTOM, CUT, TOP

get_elementid_value = get_elementid_value_func()

MAX_ELEMENT_POINTS = 20000
MAX_TOTAL_POINTS = 3000000
MAX_FORCED_POINTS = 1500000
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


def _model_category_filter(doc):
    """Return a native filter passing the elements of drawable model categories."""
    ids = List[DB.ElementId]()
    for category in doc.Settings.Categories:
        if (
            category.CategoryType == DB.CategoryType.Model
            and int(get_elementid_value(category.Id)) not in _EXCLUDED_CATEGORY_IDS
        ):
            ids.Add(category.Id)
    return DB.ElementMulticategoryFilter(ids)


def _model_element_ids(doc, scene_filter=None, host=True):
    """Return the ids of the view-independent elements of model categories.

    The ids come from one native collector pass that creates no element
    objects, so a model with hundreds of thousands of annotations and other
    non-3D elements never reaches Python.
    """
    collector = (
        DB.FilteredElementCollector(doc)
        .WhereElementIsNotElementType()
        .WhereElementIsViewIndependent()
        .WherePasses(_model_category_filter(doc))
    )
    if scene_filter is not None:
        collector = scene_filter.apply(collector, doc, host)
    return list(collector.ToElementIds())


def _model_elements(doc):
    for element_id in _model_element_ids(doc):
        element = doc.GetElement(element_id)
        if element is not None and not isinstance(element, DB.Group):
            yield element


class _Entry(object):
    __slots__ = (
        "element",
        "bbox",
        "transform",
        "link",
        "source",
        "group",
        "hidden",
        "size",
        "near",
        "lines_only",
        "requested",
    )

    def __init__(self, element, bbox, transform, link, source, group, hidden, near):
        self.element = element
        self.bbox = bbox
        self.transform = transform
        self.link = link
        self.source = source
        self.group = group
        self.hidden = hidden
        self.size = (bbox.Max - bbox.Min).GetLength()
        self.near = near
        self.lines_only = False
        self.requested = False


def _near_focus(bbox, transform, focus):
    """Tell whether ``bbox`` (in its own document) touches the world box ``focus``.

    A host element is tested by its own bounds. A linked element is first
    tested by the sphere around its transformed center, which costs one point
    transform, and only a candidate that passes gets its eight corners
    transformed for the tight test, so a long wall just outside the box does
    not outrank the geometry inside it.
    """
    if focus is None:
        return False
    if transform is None:
        low, high = bbox.Min, bbox.Max
    else:
        center = transform.OfPoint((bbox.Min + bbox.Max) * 0.5)
        radius = (bbox.Max - bbox.Min).GetLength() * 0.5
        if not _overlaps_box(
            center - DB.XYZ(radius, radius, radius),
            center + DB.XYZ(radius, radius, radius),
            focus,
        ):
            return False
        corners = [transform.OfPoint(c) for c in box_corners(bbox.Min, bbox.Max)]
        xs, ys, zs = (
            [c.X for c in corners],
            [c.Y for c in corners],
            [c.Z for c in corners],
        )
        low = DB.XYZ(min(xs), min(ys), min(zs))
        high = DB.XYZ(max(xs), max(ys), max(zs))
    return _overlaps_box(low, high, focus)


def _overlaps_box(low, high, focus):
    return (
        high.X >= focus.Min.X
        and low.X <= focus.Max.X
        and high.Y >= focus.Min.Y
        and low.Y <= focus.Max.Y
        and high.Z >= focus.Min.Z
        and low.Z <= focus.Max.Z
    )


class ModelStream(object):
    """Tessellates the model in time-sliced chunks, largest elements first.

    Args:
        doc (DB.Document): host document.
        origin (DB.XYZ): scene origin.
        include_links (bool): also stream the geometry of loaded Revit links.
        links_only (bool): stream only the links, for a page that already
            holds the host model.
        focus (DB.BoundingBoxXYZ | None): world bounds, normally of the section
            box. Elements touching it are streamed before the rest, so the
            region the user cuts appears first and is the last to be left out.
        scene_filter (sectionbox_scene_filter.SceneFilter | None): the detail
            level, phase and design options to stream; None reads every phase
            and option at Medium.

    Elements that are not 3D geometry are left out: view-specific elements,
    the categories in ``NON_GEOMETRY_CATEGORIES`` and any element without
    triangles at the detail level. Elements that are only lines there but have
    a shape at Fine, such as pipe fittings, are set aside: they are listed by
    :meth:`dropped_groups` and drawn at Fine when :meth:`load_group` asks for
    their category. One element per family type is read at Fine to decide, so
    that nothing is listed which loading would not draw. Each mesh carries its
    category as ``group`` and, for a linked
    element, the link's title as ``link``, so the page can toggle a link's walls
    apart from the host's. Rooms, spaces and parts are streamed for the host
    model flagged ``hidden`` (the page starts with their category unticked) and
    skipped in links.

    Invariant:
        Chunks are independent: the page appends meshes as they arrive. An
        element's page key is ``source`` (0 for the host, then link order) and
        its id, because link element ids can equal host ids.

    Note:
        Reading the model is time-sliced like streaming it: a chunk during the
        first phase carries no meshes and ``progress`` counts the elements
        read. ``MAX_TOTAL_POINTS`` also covers the bounding boxes drawn for
        elements that exceed their own budget. Once less than one box fits, the
        remaining, smallest elements are left out; :meth:`dropped_groups`
        lists them by category and :meth:`load_group` streams one category's
        share anyway, up to ``MAX_FORCED_POINTS`` more points. Elements deleted
        between chunks are skipped. What was loaded on request is set aside
        again when the model is streamed anew.
    """

    def __init__(
        self,
        doc,
        origin,
        include_links,
        links_only=False,
        focus=None,
        scene_filter=None,
    ):
        self.doc = doc
        self.origin = origin
        self.include_links = include_links
        self.links_only = links_only
        self.focus = focus
        self.scene_filter = scene_filter
        self.detail_level = (
            DB.ViewDetailLevel.Medium
            if scene_filter is None
            else scene_filter.detail_level
        )
        self._entries = None
        self._reading = None
        self._read_count = 0
        self._read_total = 0
        self._cursor = 0
        self._points = 0
        self._points_limit = MAX_TOTAL_POINTS
        self._dropped = []
        self._line_only = []
        self._fine_shapes = {}

    @property
    def done(self):
        """True once every prepared element has been streamed."""
        return self._entries is not None and self._cursor >= len(self._entries)

    @property
    def truncated(self):
        """Number of elements left out because the point limit was reached."""
        return len(self._dropped)

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

    def _begin_reading(self):
        queue = []
        for source, (doc, transform, title) in enumerate(self._sources()):
            if self.links_only and source == 0:
                continue
            queue.append([source, doc, transform, title, None])
        self._reading = {"queue": queue, "position": 0, "entries": []}

    def _read_some(self, deadline):
        """Read elements until ``deadline``; return True once all are read.

        The native id collection of one source cannot be interrupted, so each
        call collects at most the sources it reaches before the deadline and
        always at least one, which keeps a model with many large links from
        blocking its first chunk.
        """
        reading = self._reading
        queue = reading["queue"]
        while queue:
            source, doc, transform, title, ids = queue[0]
            if ids is None:
                ids = _model_element_ids(doc, self.scene_filter, source == 0)
                queue[0][4] = ids
                self._read_total += len(ids)
            position = reading["position"]
            while position < len(ids):
                if position % 64 == 0 and time.time() >= deadline:
                    reading["position"] = position
                    return False
                entry = self._read_entry(doc, ids[position], transform, title, source)
                position += 1
                self._read_count += 1
                if entry is not None:
                    reading["entries"].append(entry)
            queue.pop(0)
            reading["position"] = 0
            if queue and time.time() >= deadline:
                return False
        entries = reading["entries"]
        entries.sort(key=lambda entry: (entry.source, not entry.near, -entry.size))
        self._entries = entries
        self._reading = None
        return True

    def _read_entry(self, doc, element_id, transform, title, source):
        element = doc.GetElement(element_id)
        if element is None or isinstance(element, DB.Group):
            return None
        category = element.Category
        if category is None:
            return None
        hidden = _category_id(element) in _HIDDEN_BY_DEFAULT_IDS
        if title is not None and hidden:
            return None
        bbox = element_bbox(element)
        if bbox is None:
            return None
        return _Entry(
            element,
            bbox,
            transform,
            title,
            source,
            category.Name,
            hidden,
            _near_focus(bbox, transform, self.focus),
        )

    @property
    def total(self):
        """Number of elements to stream, available once they are read."""
        return len(self._entries or ())

    def dropped_groups(self):
        """List the elements not loaded as ``{source, group, link, hidden, count}``.

        These are the elements the point limit left out and those that are only
        lines at the detail level.
        """
        groups = {}
        for entry in self._dropped + self._line_only:
            key = (entry.source, entry.group)
            if key not in groups:
                groups[key] = {
                    "source": entry.source,
                    "group": entry.group,
                    "link": entry.link,
                    "hidden": entry.hidden,
                    "count": 0,
                }
            groups[key]["count"] += 1
        return list(groups.values())

    def load_group(self, source, group):
        """Queue the elements of one category that are not loaded and return how many.

        The queued elements stream in the next chunks within
        ``MAX_FORCED_POINTS`` further points; any that do not fit stay in
        :meth:`dropped_groups`. Those that are only lines at the detail level
        are read at Fine.
        """
        wanted = [
            e
            for e in self._dropped + self._line_only
            if e.source == source and e.group == group
        ]
        if not wanted:
            return 0
        wanted_ids = set(id(entry) for entry in wanted)
        self._dropped = [e for e in self._dropped if id(e) not in wanted_ids]
        self._line_only = [e for e in self._line_only if id(e) not in wanted_ids]
        for entry in wanted:
            entry.requested = True
        self._points_limit = self._points + MAX_FORCED_POINTS
        self._entries.extend(wanted)
        return len(wanted)

    def next_chunk(self, seconds):
        """Work for about ``seconds`` and return the chunk, or None when done.

        Returns:
            (dict | None): ``{"meshes": [...], "progress": [done, total]}``
            ready for :func:`scene3d.meshing.scene_to_json`.
        """
        deadline = time.time() + seconds
        if self._entries is None:
            if self._reading is None:
                self._begin_reading()
            if not self._read_some(deadline):
                return {"meshes": [], "progress": [self._read_count, self._read_total]}
        if self._cursor >= len(self._entries):
            return None
        meshes = []
        while self._cursor < len(self._entries) and time.time() < deadline:
            entry = self._entries[self._cursor]
            self._cursor += 1
            remaining = self._points_limit - self._points
            if remaining < BOX_POINT_COUNT:
                self._dropped.extend(self._entries[self._cursor - 1 :])
                self._cursor = len(self._entries)
                break
            if not entry.element.IsValidObject:
                continue
            level = DB.ViewDetailLevel.Fine if entry.lines_only else self.detail_level
            builder, approx = self._tessellate(
                entry, min(MAX_ELEMENT_POINTS, remaining), level
            )
            if not builder.indices:
                if builder.edges and level != DB.ViewDetailLevel.Fine:
                    self._set_aside(entry)
                continue
            self._points += builder.point_count
            meshes.append(
                {
                    "id": int(get_elementid_value(entry.element.Id)),
                    "source": entry.source,
                    "group": entry.group,
                    "link": entry.link,
                    "hidden": entry.hidden and entry.link is None,
                    "approx": approx,
                    "positions": FloatArray(builder.positions),
                    "indices": IntArray(builder.indices),
                }
            )
        return {"meshes": meshes, "progress": [self._cursor, len(self._entries)]}

    def _tessellate(self, entry, budget, detail_level):
        return tessellate_element(
            entry.element,
            entry.bbox,
            self.origin,
            budget,
            detail_level=detail_level,
            edges=False,
            transform=entry.transform,
            box_when_empty=False,
            coarse_retry=True,
        )

    def _has_fine_shape(self, entry):
        """Tell whether reading ``entry`` at Fine would draw it, asked once per type."""
        type_id = int(get_elementid_value(entry.element.GetTypeId()))
        key = (entry.source, type_id)
        if type_id <= 0:
            key = (entry.source, None, int(get_elementid_value(entry.element.Id)))
        if key not in self._fine_shapes:
            builder, _ = self._tessellate(
                entry, MAX_ELEMENT_POINTS, DB.ViewDetailLevel.Fine
            )
            self._fine_shapes[key] = bool(builder.indices)
        return self._fine_shapes[key]

    def _set_aside(self, entry):
        """Keep a lines-only element for loading at Fine, or queue it if asked for."""
        if not self._has_fine_shape(entry):
            return
        entry.lines_only = True
        if entry.requested:
            self._entries.append(entry)
        else:
            self._line_only.append(entry)


def _world_bounds(box):
    if box is None:
        return None
    corners = box_corners(box.Min, box.Max, box.Transform)
    bounds = DB.BoundingBoxXYZ()
    bounds.Min = DB.XYZ(
        min(c.X for c in corners), min(c.Y for c in corners), min(c.Z for c in corners)
    )
    bounds.Max = DB.XYZ(
        max(c.X for c in corners), max(c.Y for c in corners), max(c.Z for c in corners)
    )
    return bounds


def view_focus_bounds(view, datafilename):
    """Return the world bounds of the view's section or crop box, or None."""
    if not (isinstance(view, DB.View3D) or is_2d_view(view)):
        return None
    info = get_box_info(view, datafilename)
    return _world_bounds(info["box"]) if info else None


def scene_origin(doc, box):
    """Return the scene origin: the center of the model's bounds, else of ``box``."""
    bounds = union_bbox(
        [element_bbox(element) for element in _model_elements(doc)]
        + [_world_bounds(box)]
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
    """Return the crop box with its Z range replaced by the view range's extent.

    The extent runs from the top plane down to the bottom plane, or on a
    ceiling plan down to the cut plane. Without both the crop box is kept.
    """
    elevations = plane_elevations(view)
    top = elevations.get(TOP)
    bottom = elevations.get(CUT if is_ceiling_plan(view) else BOTTOM)
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
        cannot be edited, or None). Plan views with a crop box also get
        ``viewRange``, see :func:`sectionbox_viewrange.view_range_payload`.
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
            payload["viewRange"] = view_range_payload(view, origin)
    payload["box"] = box_payload(box, origin)
    return payload


def levels_payload(levels, origin):
    """Describe levels as ``{name, z, elevation, link}`` entries.

    ``z`` is relative to ``origin``, ``elevation`` is the project elevation
    shown to the user. A linked level at the elevation of one already listed is
    left out, see :func:`sectionbox_guides.drop_repeated_levels`.
    """
    entries = [
        {
            "name": level.Name,
            "z": level.ProjectElevation - origin.Z,
            "elevation": level.ProjectElevation,
            "link": hasattr(level, "SourceLink"),
        }
        for level in levels
    ]
    return drop_repeated_levels(entries)


def grids_payload(grids, origin):
    """Describe grids as ``{name, link, segs}``, segments being ``[x1, y1, x2, y2]``.

    A linked straight grid on the line of one already listed is left out, see
    :func:`sectionbox_guides.drop_repeated_grids`.
    """
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
    return drop_repeated_grids(entries)


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


def north_angle(doc):
    """Return the angle in radians from project north clockwise to true north.

    The preview's compass turns by it. A document whose project position
    cannot be read counts as unrotated.
    """
    try:
        return doc.ActiveProjectLocation.GetProjectPosition(DB.XYZ.Zero).Angle
    except Exception:
        return 0.0


def units_payload(doc):
    """Describe the project length unit for the page.

    Returns:
        (dict): ``factor`` (feet to unit), ``symbol``, ``decimals`` and
        ``dragStep``, the feet a freely dragged view range offset is rounded
        to: half an inch in imperial projects, else 10 mm.
    """
    length_unit, _, _, symbol = units.get_unit_info(DB.SpecTypeId.Length, doc)
    factor = DB.UnitUtils.Convert(1.0, DB.UnitTypeId.Feet, length_unit)
    if factor >= 100:
        decimals = 0
    elif factor < 1:
        decimals = 3
    else:
        decimals = 2
    imperial = any(abs(factor - per_foot) < 0.001 for per_foot in (1.0, 12.0))
    return {
        "factor": factor,
        "symbol": symbol or "",
        "decimals": decimals,
        "dragStep": 1.0 / 24.0 if imperial else 10.0 / 304.8,
    }
