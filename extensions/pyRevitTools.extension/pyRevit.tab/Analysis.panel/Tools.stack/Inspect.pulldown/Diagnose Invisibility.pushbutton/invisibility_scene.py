# -*- coding: utf-8 -*-
"""3D preview scene for the Diagnose Invisibility report.

Builds a JSON description of the diagnosed elements' geometry together with
the view's clipping context (section box, crop region, view range or cut
planes) for the report page's WebGL viewer.

Invariant:
    All coordinates are model feet relative to the scene ``origin`` so the
    page can upload them as 32-bit floats without visible jitter on models
    far from the internal origin.
"""

import array
import base64
import json
import re

from pyrevit import DB

from invisibility_checks import id_value, local_extents, resolve_view_range_elevation, t


MAX_SCENE_VERTICES = 60000
MAX_ELEMENT_VERTICES = 20000
_BOX_POINT_COUNT = 8 + 2 * 12
_PACKED_TOKEN = re.compile(r"@@PACKED(\d+)@@")
_MIN_PLANE_HALF_SIZE_FT = 10.0


class _BudgetExceeded(Exception):
    pass


class _FloatArray(object):
    """Marker for a large float list serialized with fixed precision."""

    __slots__ = ("values",)

    def __init__(self, values):
        self.values = values


class _IntArray(object):
    __slots__ = ("values",)

    def __init__(self, values):
        self.values = values


class _MeshBuilder(object):
    """Accumulates triangles and edge segments in scene-relative coordinates.

    Invariant:
        ``budget`` caps ``point_count``, which counts mesh vertices and edge
        endpoints alike, so curve-heavy elements cannot bypass the limits.
    """

    def __init__(self, origin, budget):
        self.origin = origin
        self.budget = budget
        self.positions = []
        self.indices = []
        self.edges = []

    @property
    def vertex_count(self):
        return len(self.positions) // 3

    @property
    def point_count(self):
        return self.vertex_count + len(self.edges) // 3

    def _reserve(self, count):
        if self.point_count + count > self.budget:
            raise _BudgetExceeded()

    def _push_vertex(self, point):
        self._reserve(1)
        self.positions.extend(
            (
                point.X - self.origin.X,
                point.Y - self.origin.Y,
                point.Z - self.origin.Z,
            )
        )
        return self.vertex_count - 1

    def add_mesh(self, mesh):
        base = self.vertex_count
        for vertex in mesh.Vertices:
            self._push_vertex(vertex)
        for index in range(mesh.NumTriangles):
            triangle = mesh.get_Triangle(index)
            self.indices.extend(
                (
                    base + triangle.get_Index(0),
                    base + triangle.get_Index(1),
                    base + triangle.get_Index(2),
                )
            )

    def add_polyline(self, points):
        points = list(points)
        self._reserve(2 * max(len(points) - 1, 0))
        for start, end in zip(points, points[1:]):
            self.edges.extend(
                (
                    start.X - self.origin.X,
                    start.Y - self.origin.Y,
                    start.Z - self.origin.Z,
                    end.X - self.origin.X,
                    end.Y - self.origin.Y,
                    end.Z - self.origin.Z,
                )
            )

    def add_box(self, bbox):
        corners = _box_corners(bbox.Min, bbox.Max)
        base = self.vertex_count
        for corner in corners:
            self._push_vertex(corner)
        for a, b, c in _BOX_TRIANGLES:
            self.indices.extend((base + a, base + b, base + c))
        for a, b in _BOX_EDGES:
            self.add_polyline((corners[a], corners[b]))


_BOX_TRIANGLES = (
    (0, 2, 1),
    (1, 2, 3),
    (4, 5, 6),
    (5, 7, 6),
    (0, 1, 4),
    (1, 5, 4),
    (2, 6, 3),
    (3, 6, 7),
    (0, 4, 2),
    (2, 4, 6),
    (1, 3, 5),
    (3, 7, 5),
)

_BOX_EDGES = (
    (0, 1),
    (1, 3),
    (3, 2),
    (2, 0),
    (4, 5),
    (5, 7),
    (7, 6),
    (6, 4),
    (0, 4),
    (1, 5),
    (2, 6),
    (3, 7),
)


def _box_corners(low, high, transform=None):
    """Return the 8 corners ordered x-fastest, then y, then z."""
    corners = [
        DB.XYZ(x, y, z)
        for z in (low.Z, high.Z)
        for y in (low.Y, high.Y)
        for x in (low.X, high.X)
    ]
    if transform is not None:
        corners = [transform.OfPoint(c) for c in corners]
    return corners


def _walk_geometry(geometry, builder):
    for item in geometry:
        if isinstance(item, DB.Solid):
            if item.Faces.Size == 0:
                continue
            for face in item.Faces:
                builder.add_mesh(face.Triangulate())
            for edge in item.Edges:
                builder.add_polyline(edge.Tessellate())
        elif isinstance(item, DB.Mesh):
            builder.add_mesh(item)
        elif isinstance(item, DB.GeometryInstance):
            _walk_geometry(item.GetInstanceGeometry(), builder)
        elif isinstance(item, DB.GeometryElement):
            _walk_geometry(item, builder)
        elif isinstance(item, DB.Curve):
            builder.add_polyline(item.Tessellate())
        elif isinstance(item, DB.PolyLine):
            builder.add_polyline(item.GetCoordinates())


def _element_geometry(element):
    options = DB.Options()
    owner_id = element.OwnerViewId
    if owner_id != DB.ElementId.InvalidElementId:
        options.View = element.Document.GetElement(owner_id)
    else:
        options.DetailLevel = DB.ViewDetailLevel.Medium
    return element.get_Geometry(options)


def _element_bbox(element):
    bbox = element.get_BoundingBox(None)
    if bbox is None and element.OwnerViewId != DB.ElementId.InvalidElementId:
        bbox = element.get_BoundingBox(element.Document.GetElement(element.OwnerViewId))
    return bbox


def _union_bbox(boxes):
    boxes = [b for b in boxes if b is not None]
    if not boxes:
        return None
    union = DB.BoundingBoxXYZ()
    union.Min = DB.XYZ(
        min(b.Min.X for b in boxes),
        min(b.Min.Y for b in boxes),
        min(b.Min.Z for b in boxes),
    )
    union.Max = DB.XYZ(
        max(b.Max.X for b in boxes),
        max(b.Max.Y for b in boxes),
        max(b.Max.Z for b in boxes),
    )
    return union


def format_length(doc, feet):
    """Format a length in feet with the project's length units."""
    try:
        return DB.UnitFormatUtils.Format(
            doc.GetUnits(), DB.SpecTypeId.Length, feet, False
        )
    except Exception:
        return "{:.2f} ft".format(feet)


def _relative(point, origin):
    return [point.X - origin.X, point.Y - origin.Y, point.Z - origin.Z]


def _vector(xyz):
    return [xyz.X, xyz.Y, xyz.Z]


def _flat(points, origin):
    values = []
    for point in points:
        values.extend(_relative(point, origin))
    return _FloatArray(values)


def _wire_box(kind, label, low, high, transform, origin):
    corners = _box_corners(low, high, transform)
    segments = []
    for a, b in _BOX_EDGES:
        segments.extend((corners[a], corners[b]))
    return {"kind": kind, "label": label, "lines": _flat(segments, origin)}


def _quad(kind, label, corners, origin):
    return {"kind": kind, "label": label, "corners": _flat(corners, origin)}


def _plane_rect(transform, scene_bbox, clip=None):
    """Return the local XY corners of a plane drawn around the elements.

    The rectangle covers the elements' extents in ``transform`` space with
    generous padding, clamped to ``clip`` (a crop box in the same space) when
    given, so planes stay readable instead of spanning a whole crop region.
    """
    low, high = local_extents(transform, scene_bbox)
    center_x = (low.X + high.X) / 2.0
    center_y = (low.Y + high.Y) / 2.0
    half_x = max((high.X - low.X) * 0.75, _MIN_PLANE_HALF_SIZE_FT)
    half_y = max((high.Y - low.Y) * 0.75, _MIN_PLANE_HALF_SIZE_FT)
    min_x, max_x = center_x - half_x, center_x + half_x
    min_y, max_y = center_y - half_y, center_y + half_y
    if clip is not None:
        clamped = (
            max(min_x, clip.Min.X),
            min(max_x, clip.Max.X),
            max(min_y, clip.Min.Y),
            min(max_y, clip.Max.Y),
        )
        if clamped[0] < clamped[1] and clamped[2] < clamped[3]:
            min_x, max_x, min_y, max_y = clamped
    return ((min_x, min_y), (max_x, min_y), (max_x, max_y), (min_x, max_y))


def _plan_overlays(view, scene_bbox, origin):
    """View range planes and crop outline for a plan view.

    Planes are labelled like Revit's View Range dialog: level plus offset.
    """
    doc = view.Document
    overlays = {"planes": [], "boxes": []}
    crop = view.CropBox if view.CropBoxActive else None
    transform = crop.Transform if crop is not None else DB.Transform.Identity
    plane_corners = [
        transform.OfPoint(DB.XYZ(x, y, 0))
        for x, y in _plane_rect(transform, scene_bbox, crop)
    ]
    crop_corners = None
    if crop is not None:
        crop_corners = [
            transform.OfPoint(DB.XYZ(x, y, 0))
            for x, y in (
                (crop.Min.X, crop.Min.Y),
                (crop.Max.X, crop.Min.Y),
                (crop.Max.X, crop.Max.Y),
                (crop.Min.X, crop.Max.Y),
            )
        ]
    try:
        view_range = view.GetViewRange()
    except Exception:
        return overlays
    planes = (
        ("top", DB.PlanViewPlane.TopClipPlane, t("plane_top", "Top")),
        ("cut", DB.PlanViewPlane.CutPlane, t("plane_cut", "Cut plane")),
        ("bottom", DB.PlanViewPlane.BottomClipPlane, t("plane_bottom", "Bottom")),
        ("depth", DB.PlanViewPlane.ViewDepthPlane, t("plane_depth", "View depth")),
    )
    cut_z = None
    for kind, plane, name in planes:
        z = resolve_view_range_elevation(doc, view_range, plane)
        if z is None:
            continue
        if kind == "cut":
            cut_z = z
        level = doc.GetElement(view_range.GetLevelId(plane))
        offset = view_range.GetOffset(plane)
        sign = "+" if offset >= 0 else "-"
        label = "{}: {} {} {}".format(
            name, level.Name if level else "?", sign, format_length(doc, abs(offset))
        )
        corners = [DB.XYZ(c.X, c.Y, z) for c in plane_corners]
        overlays["planes"].append(_quad(kind, label, corners, origin))
    if crop_corners:
        z = cut_z if cut_z is not None else scene_bbox.Min.Z
        ring = [DB.XYZ(c.X, c.Y, z) for c in crop_corners]
        segments = []
        for index in range(4):
            segments.extend((ring[index], ring[(index + 1) % 4]))
        overlays["boxes"].append(
            {
                "kind": "crop",
                "label": t("overlay_crop", "Crop region"),
                "lines": _flat(segments, origin),
            }
        )
    return overlays


def _section_overlays(view, scene_bbox, origin):
    """Cut plane, far clip plane and crop outline of a section or elevation.

    The far plane appears only when far clipping is on. The crop outline
    appears only when the crop region is active: as a box when the far plane
    bounds it, otherwise as a rectangle on the cut plane.
    """
    overlays = {"planes": [], "boxes": []}
    crop = view.CropBox
    transform = crop.Transform
    rect = _plane_rect(transform, scene_bbox, crop)

    def plane_at(z):
        return [transform.OfPoint(DB.XYZ(x, y, z)) for x, y in rect]

    overlays["planes"].append(
        _quad(
            "cut",
            t("plane_section", "Section / elevation plane"),
            plane_at(crop.Max.Z),
            origin,
        )
    )
    far_param = view.get_Parameter(DB.BuiltInParameter.VIEWER_BOUND_FAR_CLIPPING)
    far_clipped = far_param is not None and far_param.AsInteger() != 0
    if far_clipped:
        overlays["planes"].append(
            _quad(
                "far",
                "{}: {}".format(
                    t("plane_far", "Far clip"),
                    format_length(view.Document, crop.Max.Z - crop.Min.Z),
                ),
                plane_at(crop.Min.Z),
                origin,
            )
        )
    if view.CropBoxActive:
        label = t("overlay_crop", "Crop region")
        if far_clipped:
            overlays["boxes"].append(
                _wire_box("crop", label, crop.Min, crop.Max, transform, origin)
            )
        else:
            ring = [
                transform.OfPoint(DB.XYZ(x, y, crop.Max.Z))
                for x, y in (
                    (crop.Min.X, crop.Min.Y),
                    (crop.Max.X, crop.Min.Y),
                    (crop.Max.X, crop.Max.Y),
                    (crop.Min.X, crop.Max.Y),
                )
            ]
            segments = []
            for index in range(4):
                segments.extend((ring[index], ring[(index + 1) % 4]))
            overlays["boxes"].append(
                {"kind": "crop", "label": label, "lines": _flat(segments, origin)}
            )
    return overlays


def _three_d_overlays(view, origin):
    overlays = {"planes": [], "boxes": []}
    if view.IsSectionBoxActive:
        box = view.GetSectionBox()
        overlays["boxes"].append(
            _wire_box(
                "section_box",
                t("overlay_section_box", "Section box"),
                box.Min,
                box.Max,
                box.Transform,
                origin,
            )
        )
    return overlays


def _camera(view, origin):
    camera = {
        "forward": _vector(view.ViewDirection.Negate()),
        "up": _vector(view.UpDirection),
        "perspective": False,
    }
    if isinstance(view, DB.View3D):
        try:
            orientation = view.GetOrientation()
            camera["forward"] = _vector(orientation.ForwardDirection)
            camera["up"] = _vector(orientation.UpDirection)
            camera["eye"] = _relative(orientation.EyePosition, origin)
            camera["perspective"] = bool(view.IsPerspective)
        except Exception:
            pass
    return camera


def build_scene(view, element_states, label_for):
    """Describe the preview scene for one view.

    Args:
        view (DB.View): the diagnosed view.
        element_states (list[tuple[DB.Element, bool]]): elements and whether
            they are visible in the view.
        label_for (callable): element -> display label.

    Returns:
        (dict | None): scene description, or None when no element has
        extents. Elements over the per-element vertex budget, or past the
        scene budget, are drawn as their bounding box with ``approx`` set.
    """
    boxes = [
        (element, visible, _element_bbox(element))
        for element, visible in element_states
    ]
    scene_bbox = _union_bbox([b for _, _, b in boxes])
    if scene_bbox is None:
        return None
    origin = (scene_bbox.Min + scene_bbox.Max) * 0.5

    meshes = []
    remaining = MAX_SCENE_VERTICES
    for element, visible, bbox in boxes:
        if bbox is None:
            continue
        builder = _MeshBuilder(origin, min(MAX_ELEMENT_VERTICES, remaining))
        approx = remaining <= _BOX_POINT_COUNT
        if not approx:
            try:
                geometry = _element_geometry(element)
                if geometry is not None:
                    _walk_geometry(geometry, builder)
            except _BudgetExceeded:
                approx = True
            except Exception:
                approx = True
        if approx or (not builder.indices and not builder.edges):
            approx = True
            builder = _MeshBuilder(origin, _BOX_POINT_COUNT)
            builder.add_box(bbox)
        remaining = max(remaining - builder.point_count, 0)
        meshes.append(
            {
                "id": id_value(element.Id),
                "label": label_for(element),
                "visible": visible,
                "approx": approx,
                "positions": _FloatArray(builder.positions),
                "indices": _IntArray(builder.indices),
                "edges": _FloatArray(builder.edges),
            }
        )

    if isinstance(view, DB.ViewPlan):
        overlays = _plan_overlays(view, scene_bbox, origin)
    elif isinstance(view, DB.ViewSection):
        overlays = _section_overlays(view, scene_bbox, origin)
    elif isinstance(view, DB.View3D):
        overlays = _three_d_overlays(view, origin)
    else:
        overlays = {"planes": [], "boxes": []}

    return {
        "viewId": id_value(view.Id),
        "origin": _vector(origin),
        "bounds": {
            "min": _relative(scene_bbox.Min, origin),
            "max": _relative(scene_bbox.Max, origin),
        },
        "camera": _camera(view, origin),
        "meshes": meshes,
        "planes": overlays["planes"],
        "boxes": overlays["boxes"],
    }


def scene_to_json(scene):
    """Serialize a scene with large arrays packed as base64 binary.

    Float arrays become little-endian Float32 and index arrays Uint32, each
    base64-encoded into a string that ``viewer3d.js`` decodes into typed
    arrays. Formatting hundreds of thousands of numbers as JSON text takes
    over a minute on IronPython, and even ``json.dumps`` escaping megabytes
    of base64 takes seconds, so packed strings are spliced into the encoded
    skeleton by token; base64 never needs JSON escaping.
    """
    packed = []

    def pack(value):
        if isinstance(value, (_FloatArray, _IntArray)):
            typecode = "f" if isinstance(value, _FloatArray) else "I"
            packed.append(
                base64.b64encode(array.array(typecode, value.values).tostring())
            )
            return "@@PACKED{}@@".format(len(packed) - 1)
        if isinstance(value, dict):
            return dict((k, pack(v)) for k, v in value.items())
        if isinstance(value, (list, tuple)):
            return [pack(v) for v in value]
        return value

    skeleton = json.dumps(pack(scene))
    return _PACKED_TOKEN.sub(lambda match: packed[int(match.group(1))], skeleton)
