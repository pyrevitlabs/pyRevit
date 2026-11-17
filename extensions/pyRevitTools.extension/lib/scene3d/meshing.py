# -*- coding: utf-8 -*-
"""Tessellate Revit geometry into budgeted meshes and pack them as scene JSON.

Invariant:
    All coordinates handed to the page are model feet relative to a scene
    ``origin`` so the page can upload them as 32-bit floats without visible
    jitter on models far from the internal origin.
"""

import array
import base64
import json
import re

from pyrevit import DB

BOX_POINT_COUNT = 8 + 2 * 12
_PACKED_TOKEN = re.compile(r"@@PACKED(\d+)@@")


class BudgetExceeded(Exception):
    """Raised by :class:`MeshBuilder` when an element would exceed its budget."""


class FloatArray(object):
    """Marker for a float list that :func:`scene_to_json` packs as Float32."""

    __slots__ = ("values",)

    def __init__(self, values):
        self.values = values


class IntArray(object):
    """Marker for an index list that :func:`scene_to_json` packs as Uint32."""

    __slots__ = ("values",)

    def __init__(self, values):
        self.values = values


class MeshBuilder(object):
    """Accumulates triangles and edge segments in scene-relative coordinates.

    Args:
        origin (DB.XYZ): scene origin subtracted from every point.
        budget (int): cap for ``point_count``.
        transform (DB.Transform | None): applied to every point before the
            origin is subtracted, for geometry of linked models.

    Invariant:
        ``budget`` caps ``point_count``, which counts mesh vertices and edge
        endpoints alike, so curve-heavy elements cannot bypass the limits.
    """

    def __init__(self, origin, budget, transform=None):
        self.origin = origin
        self.budget = budget
        self.transform = transform
        self.positions = []
        self.indices = []
        self.edges = []

    @property
    def vertex_count(self):
        """Number of mesh vertices added so far."""
        return len(self.positions) // 3

    @property
    def point_count(self):
        """Mesh vertices plus edge endpoints, the quantity the budget limits."""
        return self.vertex_count + len(self.edges) // 3

    def _reserve(self, count):
        if self.point_count + count > self.budget:
            raise BudgetExceeded()

    def _relative(self, point):
        if self.transform is not None:
            point = self.transform.OfPoint(point)
        return (
            point.X - self.origin.X,
            point.Y - self.origin.Y,
            point.Z - self.origin.Z,
        )

    def _push_vertex(self, point):
        self._reserve(1)
        self.positions.extend(self._relative(point))
        return self.vertex_count - 1

    def add_mesh(self, mesh):
        """Add a ``DB.Mesh`` (vertices and triangles)."""
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
        """Add consecutive points as edge segments."""
        points = list(points)
        self._reserve(2 * max(len(points) - 1, 0))
        for start, end in zip(points, points[1:]):
            self.edges.extend(self._relative(start))
            self.edges.extend(self._relative(end))

    def add_box(self, bbox):
        """Add an axis-aligned ``DB.BoundingBoxXYZ`` as 12 triangles and 12 edges."""
        corners = box_corners(bbox.Min, bbox.Max)
        base = self.vertex_count
        for corner in corners:
            self._push_vertex(corner)
        for a, b, c in BOX_TRIANGLES:
            self.indices.extend((base + a, base + b, base + c))
        for a, b in BOX_EDGES:
            self.add_polyline((corners[a], corners[b]))


BOX_TRIANGLES = (
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

BOX_EDGES = (
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


def box_corners(low, high, transform=None):
    """Return the 8 corners ordered x-fastest, then y, then z.

    ``BOX_EDGES`` and ``BOX_TRIANGLES`` index into this order.
    """
    corners = [
        DB.XYZ(x, y, z)
        for z in (low.Z, high.Z)
        for y in (low.Y, high.Y)
        for x in (low.X, high.X)
    ]
    if transform is not None:
        corners = [transform.OfPoint(c) for c in corners]
    return corners


def walk_geometry(geometry, builder, edges=True):
    """Add the solids, meshes, curves and instances of ``geometry`` to ``builder``.

    Args:
        geometry (DB.GeometryElement): geometry to walk.
        builder (MeshBuilder): receives the triangles and segments.
        edges (bool): also add solid edges. Edges can be most of an element's
            point count, so previews that shade solids skip them.
    """
    for item in geometry:
        if isinstance(item, DB.Solid):
            if item.Faces.Size == 0:
                continue
            for face in item.Faces:
                triangulated = face.Triangulate()
                if triangulated is not None:
                    builder.add_mesh(triangulated)
            if edges:
                for edge in item.Edges:
                    builder.add_polyline(edge.Tessellate())
        elif isinstance(item, DB.Mesh):
            builder.add_mesh(item)
        elif isinstance(item, DB.GeometryInstance):
            walk_geometry(item.GetInstanceGeometry(), builder, edges)
        elif isinstance(item, DB.GeometryElement):
            walk_geometry(item, builder, edges)
        elif isinstance(item, DB.Curve):
            builder.add_polyline(item.Tessellate())
        elif isinstance(item, DB.PolyLine):
            builder.add_polyline(item.GetCoordinates())


def element_geometry(element, detail_level=DB.ViewDetailLevel.Medium):
    """Return the geometry of ``element`` as drawn in its owner view, if any."""
    options = DB.Options()
    owner_id = element.OwnerViewId
    if owner_id != DB.ElementId.InvalidElementId:
        options.View = element.Document.GetElement(owner_id)
    else:
        options.DetailLevel = detail_level
    return element.get_Geometry(options)


def element_bbox(element):
    """Return the model bounding box of ``element``, or its owner view's one."""
    bbox = element.get_BoundingBox(None)
    if bbox is None and element.OwnerViewId != DB.ElementId.InvalidElementId:
        bbox = element.get_BoundingBox(element.Document.GetElement(element.OwnerViewId))
    return bbox


def union_bbox(boxes):
    """Return the box enclosing all non-None ``boxes``, or None when there are none."""
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


def tessellate_element(
    element,
    bbox,
    origin,
    budget,
    detail_level=DB.ViewDetailLevel.Medium,
    edges=True,
    transform=None,
    box_when_empty=True,
):
    """Tessellate ``element`` within ``budget`` points.

    Args:
        element (DB.Element): element to tessellate.
        bbox (DB.BoundingBoxXYZ): its bounding box, drawn when the geometry
            cannot be.
        origin (DB.XYZ): scene origin.
        budget (int): point cap for this element.
        detail_level (DB.ViewDetailLevel): detail for elements without an
            owner view.
        edges (bool): also tessellate solid edges.
        transform (DB.Transform | None): maps the element's document into the
            scene, for elements of linked models.
        box_when_empty (bool): draw the bounding box of an element that has no
            geometry at all (sheets, sketches, rooms without volume). When
            False such an element returns an empty builder, so previews can
            leave it out.

    Returns:
        (tuple[MeshBuilder, bool]): the builder and whether it holds the
        bounding box only (``approx``): the budget is too small for any real
        geometry, the element exceeded it, failed to tessellate or, with
        ``box_when_empty``, has no geometry.
    """
    builder = MeshBuilder(origin, budget, transform)
    approx = budget <= BOX_POINT_COUNT
    if not approx:
        try:
            geometry = element_geometry(element, detail_level)
            if geometry is not None:
                walk_geometry(geometry, builder, edges)
        except Exception:
            approx = True
    nothing_drawn = not builder.indices and not builder.edges
    if approx or (nothing_drawn and box_when_empty):
        builder = MeshBuilder(origin, BOX_POINT_COUNT, transform)
        builder.add_box(bbox)
        return builder, True
    return builder, False


def relative(point, origin):
    """Return ``point`` minus ``origin`` as a list of three floats."""
    return [point.X - origin.X, point.Y - origin.Y, point.Z - origin.Z]


def vector(xyz):
    """Return a ``DB.XYZ`` as a list of three floats."""
    return [xyz.X, xyz.Y, xyz.Z]


def flat(points, origin):
    """Return ``points`` relative to ``origin`` as one packable float array."""
    values = []
    for point in points:
        values.extend(relative(point, origin))
    return FloatArray(values)


def _array_bytes(typecode, values):
    packed = array.array(typecode, values)
    return packed.tobytes() if hasattr(packed, "tobytes") else packed.tostring()


def scene_to_json(scene):
    """Serialize a scene with large arrays packed as base64 binary.

    Float arrays become little-endian Float32 and index arrays Uint32, each
    base64-encoded into a string that the page decodes into typed arrays.
    Formatting hundreds of thousands of numbers as JSON text takes over a
    minute on IronPython, and even ``json.dumps`` escaping megabytes of base64
    takes seconds, so packed strings are spliced into the encoded skeleton by
    token; base64 never needs JSON escaping.

    Note:
        Non-ASCII text such as element names is kept as is, not escaped as
        unicode sequences: IronPython 2's ASCII-escaping ``json.dumps`` raises
        on names that mix Cyrillic with Latin-1 characters such as guillemets.
    """
    packed = []

    def pack(value):
        if isinstance(value, (FloatArray, IntArray)):
            typecode = "f" if isinstance(value, FloatArray) else "I"
            text = base64.b64encode(_array_bytes(typecode, value.values))
            if not isinstance(text, str):
                text = text.decode("ascii")
            packed.append(text)
            return "@@PACKED{}@@".format(len(packed) - 1)
        if isinstance(value, dict):
            return dict((k, pack(v)) for k, v in value.items())
        if isinstance(value, (list, tuple)):
            return [pack(v) for v in value]
        return value

    skeleton = json.dumps(pack(scene), ensure_ascii=False)
    return _PACKED_TOKEN.sub(lambda match: packed[int(match.group(1))], skeleton)
