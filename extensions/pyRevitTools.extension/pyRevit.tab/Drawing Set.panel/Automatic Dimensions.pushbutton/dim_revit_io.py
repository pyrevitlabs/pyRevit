# -*- coding: utf-8 -*-
"""All Revit API interaction for the Automatic Dimensions rules (IronPython).

Reference strategy for dimension anchoring, in priority order:
  1. openings: the family's centerline reference (CenterLeftRight,
     then CenterFrontBack) - US practice dimensions openings to CL.
  2. wall positions: a VERTICAL PLANAR face whose normal is parallel
     to the dimension axis, near the target point IN PLAN (z ignored -
     the first live failure was caused by comparing against z=0 on an
     upper-floor plan). Exterior-side faces preferred. Mitered corner
     faces (~45 deg) are rejected by the 0.9 normal-alignment gate.
  3. fallback: the wall LOCATION-LINE ENDPOINT reference (requires
     Options.IncludeNonVisibleObjects) - covers joined/mitered wall
     ends that expose no clean axis-facing face.
"""

import dim_geometry

from Autodesk.Revit.DB import (
    UV,
    XYZ,
    Line,
    Options,
    FamilyInstance,
    FamilyInstanceReferenceType,
    FilteredElementCollector,
    BuiltInCategory,
    BuiltInParameter,
    ElementId,
    PlanViewPlane,
    Reference,
    ReferenceArray,
    SpatialElementBoundaryLocation,
    SpatialElementBoundaryOptions,
    Wall,
    WallKind,
)

FACE_NORMAL_MIN = 0.9  # rejects mitered (~0.707) corner faces
FACE_PLANE_MAX_FT = 1.5  # max plan distance target-to-face-plane
ENDPOINT_MATCH_FT = 0.1


BELOW_LEVEL_TOL_FT = 3.0
# a wall based more than this below the
# view's level belongs to the level below,
# even when it rises through the cut plane


def view_cut_elevation(doc, view):
    """Absolute elevation of the plan view's cut plane, or None when
    unavailable (non-plan view, odd view range)."""
    try:
        view_range = view.GetViewRange()
        level = doc.GetElement(view_range.GetLevelId(PlanViewPlane.CutPlane))
        if level is None:
            return None
        return level.ProjectElevation + view_range.GetOffset(PlanViewPlane.CutPlane)
    except Exception:
        return None


def make_view_wall_filter(doc, view):
    """Predicate: does this wall belong to THIS view's level?

    Two conditions (both live-motivated - below-level walls hijacked
    dimension references, and a tall below-level wall survived a
    cut-plane-only test):
      1. the wall's solid crosses the view's cut plane, AND
      2. the wall's base is not more than BELOW_LEVEL_TOL_FT below the
         view's generate-level (kills walls based on the level below
         that rise through the cut plane).
    Degrades to always-True when the view has no cut plane/level."""
    cut_z = view_cut_elevation(doc, view)
    gen_level = getattr(view, "GenLevel", None)
    base_min = None
    if gen_level is not None:
        try:
            base_min = gen_level.ProjectElevation - BELOW_LEVEL_TOL_FT
        except Exception:
            base_min = None

    def belongs(wall):
        if cut_z is None and base_min is None:
            return True
        bbox = wall.get_BoundingBox(None)
        if bbox is None:
            return False
        if cut_z is not None and not (bbox.Min.Z - 0.1 <= cut_z <= bbox.Max.Z + 0.1):
            return False
        if base_min is not None and bbox.Min.Z < base_min:
            return False
        return True

    return belongs


def get_basic_walls(doc, view):
    """Basic walls belonging to this plan view's level (cut by its cut
    plane AND based on its level - see make_view_wall_filter).

    NOTE: no Function=Exterior filtering anywhere anymore - live models
    routinely mistype it (26 of 38 partitions in the test model), so
    exterior mode relies on the user's manual selection instead."""
    belongs = make_view_wall_filter(doc, view)
    walls = []
    collector = (
        FilteredElementCollector(doc, view.Id)
        .OfCategory(BuiltInCategory.OST_Walls)
        .WhereElementIsNotElementType()
    )
    for wall in collector:
        if not isinstance(wall, Wall):
            continue
        wall_type = wall.WallType
        if wall_type is None or wall_type.Kind != WallKind.Basic:
            continue
        if not belongs(wall):
            continue
        walls.append(wall)
    return walls


def _loop_area(pts):
    """Shoelace area (sign ignored) - picks a room's outer loop."""
    total = 0.0
    for k in range(len(pts)):
        x0, y0 = pts[k]
        x1, y1 = pts[(k + 1) % len(pts)]
        total += x0 * y1 - x1 * y0
    return abs(total) / 2.0


def get_room_polygon(room):
    """The room's real boundary as ({'poly', 'wall_ids'}) or None.

    poly[k] -> poly[k+1] is edge k, and wall_ids[k] is the ElementId of
    the element that GENERATED that edge - so an edge index maps straight
    back to the wall bounding the room there. This is the whole point of
    using GetBoundarySegments instead of the room's bounding box: a bbox
    cannot say WHICH wall bounds a room, which is why the old interior
    code had to guess by nearest plane and ended up dimensioning to walls
    across the plan.

    SpatialElementBoundaryLocation.Finish puts the polygon exactly on the
    room-facing FINISH faces. The core/finish switch is applied later, to
    the face REFERENCE (core_face_reference) - the polygon stays on Finish
    because it is only used for geometry (spans, scan lines, containment).

    Curved boundary segments are reduced to their endpoints (v1 is
    rectilinear); wall_ids[k] may be None for room-separation lines, which
    the caller reports rather than silently dimensioning to nothing."""
    options = SpatialElementBoundaryOptions()
    options.SpatialElementBoundaryLocation = SpatialElementBoundaryLocation.Finish
    try:
        loops = room.GetBoundarySegments(options)
    except Exception:
        return None
    if not loops:
        return None

    best = None
    best_area = 0.0
    for loop in loops:
        pts = []
        wall_ids = []
        for segment in loop:
            try:
                curve = segment.GetCurve()
            except Exception:
                continue
            start = curve.GetEndPoint(0)
            pts.append((start.X, start.Y))
            # ElementId can come back null/invalid for walls protruding
            # into the room (Building Coder #1046) - the caller falls back
            # to matching the boundary line against any wall face there
            wall_id = getattr(segment, "ElementId", None)
            if wall_id is not None and wall_id == ElementId.InvalidElementId:
                wall_id = None
            wall_ids.append(wall_id)
        if len(pts) < 3:
            continue
        area = _loop_area(pts)
        if area > best_area:
            best_area = area
            best = {"poly": pts, "wall_ids": wall_ids}
    return best


def get_room_name(room):
    """'NEW W.I.C 7.2' - name plus number, read from the room's own
    parameters. Element.Name raised in the live run (every room came back
    as the literal fallback 'Room', which made the notes unreadable), so
    go to ROOM_NAME/ROOM_NUMBER directly and only then fall back."""
    parts = []
    for bip_name in ("ROOM_NAME", "ROOM_NUMBER"):
        bip = getattr(BuiltInParameter, bip_name, None)
        if bip is None:
            continue
        try:
            param = room.get_Parameter(bip)
            if param is not None and param.HasValue:
                text = param.AsString()
                if text:
                    parts.append(text)
        except Exception:
            pass
    if parts:
        return " ".join(parts)
    try:
        return room.Name
    except Exception:
        return "Room {0}".format(room.Id)


def get_rooms(doc, view):
    """Placed, bounded Rooms visible in the view, each with its real
    boundary polygon: [{'room', 'name', 'poly', 'wall_ids'}]. Rooms whose
    boundary cannot be read are skipped (reported by the caller)."""
    rooms = []
    collector = (
        FilteredElementCollector(doc, view.Id)
        .OfCategory(BuiltInCategory.OST_Rooms)
        .WhereElementIsNotElementType()
    )
    for room in collector:
        try:
            if room.Area <= 0:
                continue  # unplaced/unbounded
        except Exception:
            continue
        boundary = get_room_polygon(room)
        if boundary is None:
            continue
        name = get_room_name(room)
        rooms.append(
            {
                "room": room,
                "name": name,
                "poly": boundary["poly"],
                "wall_ids": boundary["wall_ids"],
            }
        )
    return rooms


# fixtures/casework/columns dimensioned to their CENTRE (user rule 3).
# Columns get both axes; the rest get one dimension to the nearest wall.
FIXTURE_CATEGORIES = ("OST_PlumbingFixtures", "OST_Casework")
COLUMN_CATEGORIES = ("OST_Columns", "OST_StructuralColumns")


def get_room_objects(doc, view):
    """Fixtures/casework/columns visible in the view, as
    [{'inst', 'pt': (x, y), 'is_column': bool}].

    Category enum members are resolved via getattr so a member missing in
    a given Revit version degrades to 'that category contributes nothing'
    instead of an import-time crash (same defensive pattern as
    get_opening_width)."""
    found = []
    groups = ((FIXTURE_CATEGORIES, False), (COLUMN_CATEGORIES, True))
    for names, is_column in groups:
        for name in names:
            bic = getattr(BuiltInCategory, name, None)
            if bic is None:
                continue
            collector = (
                FilteredElementCollector(doc, view.Id)
                .OfCategory(bic)
                .WhereElementIsNotElementType()
            )
            for inst in collector:
                if not isinstance(inst, FamilyInstance):
                    continue
                point = getattr(inst.Location, "Point", None)
                if point is None:
                    continue
                found.append(
                    {"inst": inst, "pt": (point.X, point.Y), "is_column": is_column}
                )
    return found


def face_at(faces, axis, value, inward, wall_id=None, max_ft=FACE_PLANE_MAX_FT):
    """The view-visible wall face that a room's boundary crossing sits on.

    faces:  records from collect_axis_faces(walls, axis, view)
    value:  the crossing's coordinate along `axis`
    inward: +1 if the room lies on the +axis side of this face, -1 if on
            the -axis side. The face's normal MUST point into the room -
            that is what stops a dimension binding to the far side of a
            wall and drawing its witness line through the wall body.
    wall_id: when given, only that wall's faces are considered (the fast
            path, from BoundarySegment.ElementId). Passing None searches
            every wall's faces on this axis and matches by plane
            coincidence - the fallback for the null-ElementId case.

    Nearest matching plane wins. None if nothing matches."""
    idx = 0 if axis == "x" else 1
    best = None
    best_d = None
    for f in faces:
        if wall_id is not None and f["wall"].Id != wall_id:
            continue
        if f["normal"][idx] * inward <= 0:
            continue  # face points away from the room
        d = abs(f["origin"][idx] - value)
        if d > max_ft:
            continue
        if best_d is None or d < best_d:
            best_d = d
            best = f
    return best


def get_wall_stats(doc, view):
    """Diagnostic counts: how many walls the view-based collector sees
    and how many survive each filter. NOTE: a wall outside the view
    range or hidden by filters/worksets never reaches the collector at
    all - 'visible' is the ceiling. Floors are irrelevant to all of
    this; nothing in this extension reads floors."""
    belongs = make_view_wall_filter(doc, view)
    visible = 0
    basic = 0
    this_level = 0
    collector = (
        FilteredElementCollector(doc, view.Id)
        .OfCategory(BuiltInCategory.OST_Walls)
        .WhereElementIsNotElementType()
    )
    for wall in collector:
        if not isinstance(wall, Wall):
            continue
        visible += 1
        wall_type = wall.WallType
        if wall_type is None or wall_type.Kind != WallKind.Basic:
            continue
        basic += 1
        if belongs(wall):
            this_level += 1
    return {"visible": visible, "basic": basic, "this_level": this_level}


def get_wall_endpoints(wall):
    """LocationCurve endpoints as ((x, y), (x, y)). ValueError if curved."""
    curve = getattr(wall.Location, "Curve", None)
    if curve is None or not isinstance(curve, Line):
        raise ValueError(
            "Wall {0} is curved or has no straight location line".format(wall.Id)
        )
    p0 = curve.GetEndPoint(0)
    p1 = curve.GetEndPoint(1)
    return (p0.X, p0.Y), (p1.X, p1.Y)


# Openings are looked up one wall at a time, but the document-wide scan
# behind that lookup happens ONCE per run and is indexed by host. Doing
# it inside the per-wall loop rescanned every door and window in the
# model for every wall.
_OPENING_INDEX = {}


def reset_opening_cache():
    """Drop the opening index. Callers must do this at the start of every
    run: pyRevit reuses its engine between runs, so an index built from a
    previous state of the model would otherwise survive into the next."""
    _OPENING_INDEX.clear()


def _opening_index(doc, doors_only):
    """Host ElementId -> list of door/window FamilyInstances it hosts."""
    cached = _OPENING_INDEX.get(doors_only)
    if cached is not None:
        return cached
    if doors_only:
        categories = (BuiltInCategory.OST_Doors,)
    else:
        categories = (BuiltInCategory.OST_Doors, BuiltInCategory.OST_Windows)
    index = {}
    for bic in categories:
        collector = (
            FilteredElementCollector(doc).OfCategory(bic).WhereElementIsNotElementType()
        )
        for inst in collector:
            if isinstance(inst, FamilyInstance) and inst.Host is not None:
                index.setdefault(inst.Host.Id, []).append(inst)
    _OPENING_INDEX[doors_only] = index
    return index


def get_hosted_openings(wall, doc, doors_only=False):
    """Door/window FamilyInstances hosted by this wall."""
    return _opening_index(doc, doors_only).get(wall.Id, [])


def get_opening_point(instance):
    """(x, y) of a door/window, for projection math only."""
    point = getattr(instance.Location, "Point", None)
    if point is None:
        raise ValueError("Opening {0} has no location point".format(instance.Id))
    return (point.X, point.Y)


def get_opening_centerline_reference(instance):
    """Centerline Reference of a door/window, or ValueError naming the
    element if its family exposes no centerline reference."""
    for ref_type in (
        FamilyInstanceReferenceType.CenterLeftRight,
        FamilyInstanceReferenceType.CenterFrontBack,
    ):
        refs = list(instance.GetReferences(ref_type))
        if refs:
            return refs[0]
    raise ValueError(
        "Door/window {0} exposes no centerline reference - skipped".format(instance.Id)
    )


def get_opening_side_references(instance):
    """(left_ref, right_ref) for rough-opening style dimensioning, from
    the family's Left/Right references. Returns None if the family does
    not expose both (caller falls back to centerline). The exact plane
    (R.O. vs panel width) depends on how the family was built."""
    lefts = list(instance.GetReferences(FamilyInstanceReferenceType.Left))
    rights = list(instance.GetReferences(FamilyInstanceReferenceType.Right))
    if lefts and rights:
        return lefts[0], rights[0]
    return None


def get_opening_width(instance):
    """Opening width in feet for positioning math (Rough Width preferred,
    then Width), from instance then type. None if not found - caller
    then uses centerline positioning for that opening.

    Enum member names resolved via getattr because they could not be
    verified against RevitAPI.dll offline - a missing member silently
    degrades to the next candidate instead of crashing."""
    holders = (instance, instance.Symbol)
    for bip_name in (
        "FAMILY_ROUGH_WIDTH_PARAM",
        "DOOR_WIDTH",
        "WINDOW_WIDTH",
        "FAMILY_WIDTH_PARAM",
    ):
        bip = getattr(BuiltInParameter, bip_name, None)
        if bip is None:
            continue
        for holder in holders:
            if holder is None:
                continue
            param = holder.get_Parameter(bip)
            if param is not None and param.HasValue:
                width = param.AsDouble()
                if width > 0:
                    return width
    return None


def get_wall_centerline_reference(wall):
    """Reference of the wall's invisible location line, for interior
    partition-centerline dimensioning. None if not found."""
    try:
        curve = wall.Location.Curve
        c0 = curve.GetEndPoint(0)
        c1 = curve.GetEndPoint(1)
    except Exception:
        return None

    options = Options()
    options.ComputeReferences = True
    options.IncludeNonVisibleObjects = True
    for geom_obj in wall.get_Geometry(options):
        if not isinstance(geom_obj, Line):
            continue
        if geom_obj.Reference is None:
            continue
        g0 = geom_obj.GetEndPoint(0)
        g1 = geom_obj.GetEndPoint(1)
        # match against the location curve (either direction)
        same = (g0.DistanceTo(c0) < 0.5 and g1.DistanceTo(c1) < 0.5) or (
            g0.DistanceTo(c1) < 0.5 and g1.DistanceTo(c0) < 0.5
        )
        if same:
            return geom_obj.Reference
    return None


def get_instance_center_reference(instance, axis, frame=None):
    """Center reference of a fixture/casework instance for dimensioning
    along `axis`. Picks CenterLeftRight vs CenterFrontBack based on the
    instance's HandOrientation (heuristic - families vary). None if the
    family exposes neither. HandOrientation is compared in FRAME-LOCAL
    coordinates, so a fixture in an angled wing picks the same reference
    its orthogonal twin would."""
    if frame is None:
        frame = dim_geometry.Frame(0.0)
    hand = getattr(instance, "HandOrientation", None)
    prefer_lr = True
    if hand is not None:
        local = frame.to_local((hand.X, hand.Y))
        along = abs(local[0]) if axis == "x" else abs(local[1])
        prefer_lr = along > 0.7
    if prefer_lr:
        order = (
            FamilyInstanceReferenceType.CenterLeftRight,
            FamilyInstanceReferenceType.CenterFrontBack,
        )
    else:
        order = (
            FamilyInstanceReferenceType.CenterFrontBack,
            FamilyInstanceReferenceType.CenterLeftRight,
        )
    for ref_type in order:
        refs = list(instance.GetReferences(ref_type))
        if refs:
            return refs[0]
    return None


def collect_axis_faces(walls, axis, view=None, frame=None):
    """Pre-compute all dimensionable faces for the given axis.

    Returns a list of dicts with keys ref/origin/normal/exterior:
    vertical planar faces whose normal is parallel to `axis`
    (within FACE_NORMAL_MIN), from every wall given. `exterior` is
    True when the face normal points the same way as Wall.Orientation.

    view: when given, geometry is computed VIEW-AWARE (Options.View),
    so the returned face references are guaranteed VISIBLE in that
    view. This is required for interior opening strings - their raw
    model-geometry references produced dimensions that existed but
    rendered in no view (forensics: bbox None). Room lines/exterior
    call WITHOUT a view (default) and are intentionally unchanged.

    frame: the building direction this pass is working in. `origin` and
    `normal` come back in FRAME-LOCAL coordinates, and the axis-alignment
    gate is applied to the LOCAL normal - so a wall of an angled wing
    passes its own frame's gate exactly as an orthogonal wall passes the
    world one. Frame(0) is the exact identity, so orthogonal models are
    bit-for-bit unchanged. Without this, every face of a rotated wall has
    normal components of ~0.7 and is rejected by FACE_NORMAL_MIN - which
    is why angled buildings lost their anchors entirely.
    """
    if frame is None:
        frame = dim_geometry.Frame(0.0)
    options = Options()
    options.ComputeReferences = True
    if view is not None:
        options.View = view

    faces = []
    for wall in walls:
        orientation = getattr(wall, "Orientation", None)
        for geom_obj in wall.get_Geometry(options):
            solid_faces = getattr(geom_obj, "Faces", None)
            if solid_faces is None:
                continue
            for face in solid_faces:
                bbox = face.GetBoundingBox()
                mid = UV(
                    (bbox.Min.U + bbox.Max.U) / 2.0, (bbox.Min.V + bbox.Max.V) / 2.0
                )
                normal = face.ComputeNormal(mid)
                if abs(normal.Z) > 0.1:
                    continue  # top/bottom faces
                local_n = frame.to_local((normal.X, normal.Y))
                aligned = abs(local_n[0]) if axis == "x" else abs(local_n[1])
                if aligned < FACE_NORMAL_MIN:
                    continue  # long faces and mitered corner faces
                if face.Reference is None:
                    continue
                center = face.Evaluate(mid)
                is_ext = (
                    orientation is not None
                    and (normal.X * orientation.X + normal.Y * orientation.Y) > 0.5
                )
                faces.append(
                    {
                        "ref": face.Reference,
                        "wall": wall,
                        "origin": frame.to_local((center.X, center.Y)),
                        "normal": local_n,
                        "exterior": is_ext,
                    }
                )
    return faces


def exterior_face_perps(walls, axis, frame=None):
    """Perpendicular coordinates (frame-local) of the walls' exterior
    LONG faces, for a run measuring along `axis`.

    A run measuring along x is bounded by faces whose normals point in
    y - so this collects the PERPENDICULAR axis's faces and returns
    each one's plane position. Used to snap the dimension-line base
    from the location-line extreme out to the real finish face
    (geometry.snap_base_outward): measured per wall, never guessed
    from Wall.Width, because the location line can sit anywhere in the
    wall depending on its Location Line setting."""
    perp_axis = "y" if axis == "x" else "x"
    pidx = 1 if axis == "x" else 0
    perps = []
    for f in collect_axis_faces(walls, perp_axis, None, frame):
        if f["exterior"]:
            perps.append(f["origin"][pidx])
    return perps


def find_face_reference(axis_faces, pt_xy, prefer_exterior=True):
    """Best face record for a target plan point, or None if nothing
    within FACE_PLANE_MAX_FT.

    prefer_exterior=True (exterior mode): exterior shell faces win
    first, then plane distance - the consistent perimeter drafter rule.
    prefer_exterior=False (interior strings): nearest plane wins -
    partitions' 'exterior' flag is arbitrary and preferring it made
    witness lines jump through walls (live feedback)."""
    best = None
    best_key = None
    for f in axis_faces:
        ox, oy = f["origin"]
        nx, ny = f["normal"]
        plane_d = abs(nx * (pt_xy[0] - ox) + ny * (pt_xy[1] - oy))
        if plane_d > FACE_PLANE_MAX_FT:
            continue
        center_d = ((pt_xy[0] - ox) ** 2 + (pt_xy[1] - oy) ** 2) ** 0.5
        if prefer_exterior:
            key = (0 if f["exterior"] else 1, round(plane_d, 1), center_d)
        else:
            key = (round(plane_d, 1), center_d)
        if best_key is None or key < best_key:
            best_key = key
            best = f
    return best


def outermost_same_face(axis_faces, face_info, axis, window_ft=0.5):
    """The outermost face of the SAME wall on the SAME side as face_info.

    A wall solid can present more than one face on one side, a fraction of
    an inch apart (finish layer vs what sits behind it). find_face_reference
    scores by distance to the target, so it lands on the NEARER of them -
    i.e. one step INSIDE the finish face. Live audit, wall 5298947:

        --> @ 10'-5.1" | outer | 0.267 ft from target   <- was chosen
            @ 10'-5.4" | outer | 0.297 ft from target   <- the finish face

    This walks outward along the face normal to the last face of that same
    wall on that same side. It CANNOT change which wall or which side was
    chosen - so a wall that exposes a single face per side is unaffected,
    and only the reported defect moves."""
    idx = 0 if axis == "x" else 1
    if abs(face_info["normal"][idx]) < 0.5:
        return face_info

    # the decision itself is pure and unit-tested (geometry.outermost_index,
    # exercised against the real face-audit numbers from the live model)
    faces = [face_info] + [f for f in axis_faces if f is not face_info]
    items = [(str(f["wall"].Id), f["origin"][idx], f["normal"][idx]) for f in faces]
    return faces[dim_geometry.outermost_index(items, 0, window_ft)]


def face_candidates(axis_faces, pt_xy, max_ft=FACE_PLANE_MAX_FT):
    """Every face find_face_reference could legally have picked for this
    target point, nearest plane first.

    Diagnostic only. Exterior dimensions were reported landing an arbitrary
    distance INSIDE the finish face, which means the wrong plane is winning
    the contest in find_face_reference - this shows the whole contest
    (which wall, which coordinate, exterior side or not, how far) so the
    losing/winning faces can be compared against the model instead of
    guessed at."""
    out = []
    for f in axis_faces:
        ox, oy = f["origin"]
        nx, ny = f["normal"]
        plane_d = abs(nx * (pt_xy[0] - ox) + ny * (pt_xy[1] - oy))
        if plane_d > max_ft:
            continue
        out.append(
            {
                "wall_id": f["wall"].Id,
                "origin": f["origin"],
                "normal": f["normal"],
                "exterior": f["exterior"],
                "plane_d": plane_d,
            }
        )
    out.sort(key=lambda c: c["plane_d"])
    return out


def get_jamb_faces(instance, axis, center_value, width, frame=None):
    """R.O. fallback when a door/window family exposes no Left/Right
    references: the opening CUT itself creates real jamb faces in the
    HOST WALL's solid, with normals along the wall's run axis. Returns
    (left_face, right_face) face records nearest the opening center on
    each side, or None. center_value is frame-local."""
    host = getattr(instance, "Host", None)
    if host is None or not isinstance(host, Wall):
        return None
    idx = 0 if axis == "x" else 1
    window = (width / 2.0 + 0.75) if width else 2.5
    left = None
    right = None
    for face in collect_axis_faces([host], axis, None, frame):
        delta = face["origin"][idx] - center_value
        if -window <= delta < 0:
            if left is None or face["origin"][idx] > left["origin"][idx]:
                left = face
        elif 0 < delta <= window:
            if right is None or face["origin"][idx] < right["origin"][idx]:
                right = face
    if left is not None and right is not None:
        return left, right
    return None


def jamb_faces_from(faces, center_value, idx, width):
    """From a precollected face list (typically ONE host wall's
    view-aware axis faces), the two faces flanking an opening center -
    the rough-opening jambs. Returns (left, right) or None."""
    window = (width / 2.0 + 0.75) if width else 2.5
    left = None
    right = None
    for face in faces:
        delta = face["origin"][idx] - center_value
        if -window <= delta < 0:
            if left is None or face["origin"][idx] > left["origin"][idx]:
                left = face
        elif 0 < delta <= window:
            if right is None or face["origin"][idx] < right["origin"][idx]:
                right = face
    if left is not None and right is not None:
        return left, right
    return None


def _shell_thicknesses(wall):
    """(exterior_shell_ft, interior_shell_ft, total_ft) from the wall
    type's CompoundStructure - the finish thicknesses outside the core
    on each side. None if the wall has no core."""
    structure = wall.WallType.GetCompoundStructure()
    if structure is None:
        return None
    first = structure.GetFirstCoreLayerIndex()
    last = structure.GetLastCoreLayerIndex()
    if first < 0 or last < 0:
        return None
    ext = 0.0
    for i in range(first):
        ext += structure.GetLayerWidth(i)
    inte = 0.0
    for i in range(last + 1, structure.LayerCount):
        inte += structure.GetLayerWidth(i)
    return ext, inte, structure.GetWidth()


def calibrate_core_indices(wall, view, doc, frame=None):
    """Find which stable-reference indices are THIS wall's core faces,
    by MEASUREMENT instead of the fixed 1-4 table: the fixed table
    ("{UniqueId}:-9999:{index}", Building Coder #1684) is unreliable -
    both that article and a Dynamo-forum reverse-engineering thread
    confirm the index varies between wall types with no known formula.

    Method: for each candidate index, create a TEMPORARY dimension from
    the wall's exterior finish face to the candidate reference, read
    its value, delete it, and keep the index whose measured distance
    equals the shell thickness computed from the CompoundStructure.
    Must run inside an open Transaction. Returns
    {"exterior": idx, "interior": idx} (possibly partial) or None."""
    shells = _shell_thicknesses(wall)
    if shells is None:
        return None
    ext_shell, int_shell, total = shells

    if frame is None:
        frame = dim_geometry.Frame(0.0)
    orientation = getattr(wall, "Orientation", None)
    if orientation is None:
        return None
    # the wall's own frame decides which local axis its faces face along -
    # using world X/Y here found no faces on an angled wall, so core mode
    # silently fell back to finish for the whole wing
    local_o = frame.to_local((orientation.X, orientation.Y))
    axis = "x" if abs(local_o[0]) >= abs(local_o[1]) else "y"
    ext_face = None
    for f in collect_axis_faces([wall], axis, None, frame):
        if f["exterior"]:
            ext_face = f
            break
    if ext_face is None:
        return None

    curve = getattr(wall.Location, "Curve", None)
    if curve is None:
        return None
    mid = curve.Evaluate(0.5, True)
    p0 = XYZ(mid.X - orientation.X * 5.0, mid.Y - orientation.Y * 5.0, mid.Z)
    p1 = XYZ(mid.X + orientation.X * 5.0, mid.Y + orientation.Y * 5.0, mid.Z)
    line = Line.CreateBound(p0, p1)

    layer_count = wall.WallType.GetCompoundStructure().LayerCount
    tol = 0.004  # ~1/20"
    found = {}
    for idx in range(0, 2 * layer_count + 6):
        stable = "{0}:-9999:{1}".format(wall.UniqueId, idx)
        try:
            ref = Reference.ParseFromStableRepresentation(doc, stable)
        except Exception:
            continue
        ref_array = ReferenceArray()
        ref_array.Append(ext_face["ref"])
        ref_array.Append(ref)
        dim = None
        try:
            dim = doc.Create.NewDimension(view, line, ref_array)
            value = dim.Value
        except Exception:
            value = None
        if dim is not None:
            doc.Delete(dim.Id)
        if value is None:
            continue
        if "exterior" not in found and abs(value - ext_shell) <= tol:
            found["exterior"] = idx
        if "interior" not in found and abs(value - (total - int_shell)) <= tol:
            found["interior"] = idx
        if "exterior" in found and "interior" in found:
            break
    return found or None


def core_face_reference(face_info, view, doc, cache, notes, frame=None):
    """Reference to the wall's CORE boundary on the same side as the
    given finish face ("face of stud"). Uses per-wall measured
    calibration (see calibrate_core_indices), cached by wall id.
    Returns None (caller falls back to finish face) when the wall has
    no core or calibration finds nothing."""
    wall = face_info["wall"]
    key = str(wall.Id)
    if key not in cache:
        try:
            cache[key] = calibrate_core_indices(wall, view, doc, frame)
        except Exception as ex:
            cache[key] = None
            notes.append("Wall {0}: core calibration raised {1}".format(wall.Id, ex))
        if cache[key] is None:
            notes.append(
                "Wall {0}: no core reference found - finish face used".format(wall.Id)
            )
    calibration = cache[key]
    if not calibration:
        return None
    side = "exterior" if face_info["exterior"] else "interior"
    idx = calibration.get(side)
    if idx is None:
        return None
    stable = "{0}:-9999:{1}".format(wall.UniqueId, idx)
    return Reference.ParseFromStableRepresentation(doc, stable)


def get_centerline_end_reference(wall, pt_xy):
    """Fallback: Reference of the wall location-line endpoint at pt_xy.
    Requires IncludeNonVisibleObjects (the location line is invisible
    geometry). Returns None if not found."""
    options = Options()
    options.ComputeReferences = True
    options.IncludeNonVisibleObjects = True
    for geom_obj in wall.get_Geometry(options):
        if not isinstance(geom_obj, Line):
            continue
        for i in (0, 1):
            end = geom_obj.GetEndPoint(i)
            d = ((end.X - pt_xy[0]) ** 2 + (end.Y - pt_xy[1]) ** 2) ** 0.5
            if d <= ENDPOINT_MATCH_FT:
                ref = geom_obj.GetEndPointReference(i)
                if ref is not None:
                    return ref
    return None


def create_dimension_tier(
    doc,
    view,
    references,
    axis,
    value_range,
    perpendicular_position,
    base_z=0.0,
    frame=None,
):
    """One dimension string via Document.Create.NewDimension.
    Caller manages the Transaction. Duplicate references (same stable
    representation - e.g. a wall-end face that is also an opening jamb)
    are silently collapsed; NewDimension rejects arrays containing the
    same reference twice.

    value_range and perpendicular_position are FRAME-LOCAL; the dimension
    line is rotated back into world coordinates here. A dimension always
    measures ALONG its line, so on an angled building a world-axis line
    would return the cosine-shortened projection of the wall - the wrong
    number. Frame(0) is the exact identity."""
    if frame is None:
        frame = dim_geometry.Frame(0.0)
    ref_array = ReferenceArray()
    seen = []
    for ref in references:
        try:
            stable = ref.ConvertToStableRepresentation(doc)
        except Exception:
            stable = None
        if stable is not None and stable in seen:
            continue
        if stable is not None:
            seen.append(stable)
        ref_array.Append(ref)

    lo, hi = value_range
    margin = 1.0
    if axis == "x":
        local0 = (lo - margin, perpendicular_position)
        local1 = (hi + margin, perpendicular_position)
    else:
        local0 = (perpendicular_position, lo - margin)
        local1 = (perpendicular_position, hi + margin)

    w0 = frame.to_world(local0)
    w1 = frame.to_world(local1)
    p0 = XYZ(w0[0], w0[1], base_z)
    p1 = XYZ(w1[0], w1[1], base_z)

    return doc.Create.NewDimension(view, Line.CreateBound(p0, p1), ref_array)
