# -*- coding: utf-8 -*-
"""Pure geometry logic for the Automatic Dimensions rules.

Zero Revit dependency - unit-tested anywhere (tests/test_geometry.py).
Dual-engine: IronPython 2.7 (pyRevit) and CPython 3.x (tests). No
f-strings, no annotations, explicit float division only.

Points are (x, y) tuples in decimal feet. Segments are (point, point).

Pipeline:
  order_segments()  unordered wall segments -> connected chains.
                    Two phases: exact endpoint chaining, then gap
                    bridging - real models have split walls, offset
                    bumps and unjoined corners whose location lines
                    do not touch (live-observed: one house perimeter
                    fragmented into 25 "sides" without bridging).
  split_runs()      one chain -> maximal SINGLE-AXIS runs. Since the
                    script groups runs per facing direction afterwards,
                    splitting no longer tries to preserve whole "sides"
                    - every axis change is a boundary. Micro-segments
                    (< RECT_MIN_SEG_FT, e.g. offset-bump connectors)
                    inherit their neighbors' axis when those agree, so
                    an offset bump stays inside one run as a jog;
                    micro-runs made only of bridged connectors are
                    dropped. (The old long-stretch "side" grouping
                    failed live on a 3.7 ft x 7 ft bump-out - real
                    walls under the 4 ft threshold became clutter and
                    the whole west side was skipped.)
  build_tiers()     one run -> the 3-tier exterior dimension values.

Gap-bridged connector segments carry seg-index None - callers mapping
seg indices back to walls must skip None.
"""
from __future__ import division

import math

TOLERANCE_FT = 0.01        # exact endpoint-matching tolerance
GAP_TOL_FT = 2.0           # bridge splits/bumps/unjoined ends up to this
COLLINEAR_OFFSET_FT = 0.2  # same-line tolerance for unlimited-length
                           # collinear bridging (string runs across a
                           # storefront/opening break like a drafter's)
ANGLE_TOL_DEG = 1.0        # direction-change threshold
RECT_MIN_SEG_FT = 1.0      # segments shorter than this are exempt from
                           # the rectilinearity check and get their axis
                           # from their neighbors (micro-connectors)
TIER_MERGE_TOL_FT = 0.15   # tier values closer than ~2" merge into one
                           # witness line (bridged connectors can create
                           # near-coincident jog points)
FRAME_TOL_DEG = 2.0        # walls within this of a frame's angle belong
                           # to it (models are never perfectly on-angle)
FRAME_MIN_LEN_FT = 1.0     # stubs are too short to vote on a direction
WITNESS_END_TOL_FT = 1.0   # a wall this close to either end of a witness
                           # line does not count as "crossed" (absorbs the
                           # location-line vs finish-face offset)

QUARTER_TURN = math.pi / 2.0


class GeometryError(Exception):
    """Base for geometry failures. Message is user-facing."""


# ------------------------------------------------------- rotated frames
#
# Everything below this module's frame layer works in a LOCAL coordinate
# system whose x/y axes run along the building. For an orthogonal building
# that is the world system and Frame(0) is the exact identity, so nothing
# changes. For an angled building - or an angled WING of an otherwise
# orthogonal one - each direction gets its own Frame, and the same tier /
# room / span math runs inside it unchanged.
#
# This is the only honest way to fix angled buildings: a dimension is
# always created ALONG a line, so measuring a rotated wall against a world
# axis returns the cosine-shortened projection - the wrong number, not
# merely a badly placed one.


class Frame(object):
    """A building direction. Rotates between world and frame-local (x, y).

    angle is measured from world +X, and only matters modulo a quarter
    turn: a frame's x and y axes are interchangeable for our purposes, so
    0 deg and 90 deg are the same frame."""

    def __init__(self, angle=0.0):
        self.angle = angle
        # exact identity at 0 so orthogonal models are bit-for-bit
        # unchanged and cannot regress
        if angle == 0.0:
            self.cos = 1.0
            self.sin = 0.0
        else:
            self.cos = math.cos(angle)
            self.sin = math.sin(angle)

    def to_local(self, pt):
        x, y = pt
        return (x * self.cos + y * self.sin, -x * self.sin + y * self.cos)

    def to_world(self, pt):
        u, v = pt
        return (u * self.cos - v * self.sin, u * self.sin + v * self.cos)

    def degrees(self):
        return math.degrees(self.angle)

    def __repr__(self):
        return "Frame({0:.2f} deg)".format(self.degrees())


def _circular_distance(a, b, period=QUARTER_TURN):
    d = abs(a - b) % period
    return min(d, period - d)


def segment_angle(p, q):
    """Direction of a segment, folded into [0, 90) - a wall and the wall
    perpendicular to it define the same frame."""
    return math.atan2(q[1] - p[1], q[0] - p[0]) % QUARTER_TURN


def direction_frames(segments, tol_deg=FRAME_TOL_DEG,
                     min_len=FRAME_MIN_LEN_FT):
    """The building's directions, as Frames, most important first.

    Wall directions are folded modulo 90 deg and clustered, each wall
    voting with its LENGTH - so a long facade sets the frame and a short
    closet stub cannot. An orthogonal building yields exactly one frame at
    ~0 deg; a rotated one yields one frame at its angle; an angled wing
    yields a second frame.

    The cluster's angle is a length-weighted CIRCULAR mean (taken on the
    4x-angle unit circle, so 89 deg and 1 deg average to 90/0, not 45)."""
    votes = []
    for p, q in segments:
        length = _dist(p, q)
        if length < min_len:
            continue
        votes.append((segment_angle(p, q), length))
    if not votes:
        return [Frame(0.0)]

    tol = math.radians(tol_deg)
    clusters = []  # [[(angle, weight)], ...] seeded by the longest walls
    for angle, weight in sorted(votes, key=lambda v: -v[1]):
        for cluster in clusters:
            if _circular_distance(angle, cluster[0][0]) <= tol:
                cluster.append((angle, weight))
                break
        else:
            clusters.append([(angle, weight)])

    frames = []
    for cluster in clusters:
        # circular mean at 4x so the [0, 90) wrap averages correctly
        sx = sy = 0.0
        total = 0.0
        for angle, weight in cluster:
            sx += weight * math.cos(4.0 * angle)
            sy += weight * math.sin(4.0 * angle)
            total += weight
        mean = (math.atan2(sy, sx) / 4.0) % QUARTER_TURN
        frames.append((mean, total))

    frames.sort(key=lambda f: -f[1])
    return [Frame(angle) for angle, _ in frames]


def frame_of(segment, frames, tol_deg=FRAME_TOL_DEG):
    """Index of the frame a wall belongs to, or None when it is on no
    frame at all (a genuinely skewed wall - reported, never dimensioned
    against the wrong axis)."""
    angle = segment_angle(segment[0], segment[1])
    tol = math.radians(tol_deg)
    best = None
    best_d = None
    for i in range(len(frames)):
        d = _circular_distance(angle, frames[i].angle % QUARTER_TURN)
        if d > tol:
            continue
        if best_d is None or d < best_d:
            best_d = d
            best = i
    return best


class NotRectilinearError(GeometryError):
    pass


class MultiDirectionalChainError(GeometryError):
    """No longer raised (kept for import compatibility): single-axis
    splitting makes multi-directional runs structurally impossible."""


def _dist(p, q):
    return ((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2) ** 0.5


def _heading(p, q):
    return math.atan2(q[1] - p[1], q[0] - p[0])


def _is_turn(p_prev, p, p_next, angle_tol_deg):
    diff = abs(math.degrees(_heading(p, p_next) - _heading(p_prev, p)))
    diff = min(diff, 360.0 - diff)
    return diff > angle_tol_deg


# ------------------------------------------------------------- chaining

def _exact_chains(segments, tol):
    """Phase 1: chain segments whose endpoints coincide within tol."""
    chains = []
    unused = set(range(len(segments)))

    while unused:
        start = min(unused)
        unused.discard(start)
        pts = [segments[start][0], segments[start][1]]
        idxs = [start]

        def walk(get_end, add_pt, add_idx):
            changed = True
            while changed:
                changed = False
                end = get_end()
                for i in sorted(unused):
                    a, b = segments[i]
                    if _dist(a, end) <= tol:
                        add_pt(b)
                        add_idx(i)
                        unused.discard(i)
                        changed = True
                        break
                    if _dist(b, end) <= tol:
                        add_pt(a)
                        add_idx(i)
                        unused.discard(i)
                        changed = True
                        break

        walk(lambda: pts[-1], pts.append, idxs.append)
        walk(lambda: pts[0],
             lambda p: pts.insert(0, p),
             lambda i: idxs.insert(0, i))

        closed = len(pts) > 3 and _dist(pts[0], pts[-1]) <= tol
        if closed:
            pts = pts[:-1]
        chains.append((pts, idxs, closed))

    return chains


def _end_point(chain_pts, end):
    return chain_pts[0] if end == 0 else chain_pts[-1]


def _end_axis(chain_pts, end):
    """Axis of the segment at a chain end; None if degenerate."""
    if len(chain_pts) < 2:
        return None
    if end == 0:
        p, q = chain_pts[1], chain_pts[0]
    else:
        p, q = chain_pts[-2], chain_pts[-1]
    dx = abs(q[0] - p[0])
    dy = abs(q[1] - p[1])
    if dx < 1e-9 and dy < 1e-9:
        return None
    return "x" if dx >= dy else "y"


def _collinear_bridge_ok(pts_i, end_i, pts_j, end_j, collinear_offset):
    """True when two chain ends lie on the same axis-aligned line, so
    they may be bridged regardless of gap length."""
    axis_i = _end_axis(pts_i, end_i)
    axis_j = _end_axis(pts_j, end_j)
    if axis_i is None or axis_j is None or axis_i != axis_j:
        return False
    pi = _end_point(pts_i, end_i)
    pj = _end_point(pts_j, end_j)
    perp = abs(pj[1] - pi[1]) if axis_i == "x" else abs(pj[0] - pi[0])
    return perp <= collinear_offset


def _merge_chains(chains, gap_tol, collinear_offset):
    """Phase 2: bridge open chains across small gaps (any direction) or
    collinear gaps (any length). Connector segments get index None."""
    closed = [c for c in chains if c[2]]
    open_chains = [[c[0], c[1]] for c in chains if not c[2]]

    merged = True
    while merged and len(open_chains) > 1:
        merged = False
        best = None  # (gap, i, j, end_i, end_j)
        for i in range(len(open_chains)):
            for j in range(i + 1, len(open_chains)):
                for end_i in (0, 1):
                    for end_j in (0, 1):
                        pi = _end_point(open_chains[i][0], end_i)
                        pj = _end_point(open_chains[j][0], end_j)
                        gap = _dist(pi, pj)
                        ok = (gap <= gap_tol
                              or _collinear_bridge_ok(
                                  open_chains[i][0], end_i,
                                  open_chains[j][0], end_j,
                                  collinear_offset))
                        if ok and (best is None or gap < best[0]):
                            best = (gap, i, j, end_i, end_j)
        if best is not None:
            _, i, j, end_i, end_j = best
            pts_i, idxs_i = open_chains[i]
            pts_j, idxs_j = open_chains[j]
            if end_i == 0:   # connect at i's head -> flip i tail-first
                pts_i = pts_i[::-1]
                idxs_i = idxs_i[::-1]
            if end_j == 1:   # connect at j's tail -> flip j head-first
                pts_j = pts_j[::-1]
                idxs_j = idxs_j[::-1]
            open_chains[i] = [pts_i + pts_j, idxs_i + [None] + idxs_j]
            open_chains.pop(j)
            merged = True

    result = list(closed)
    for pts, idxs in open_chains:
        if len(pts) > 3 and _dist(pts[0], pts[-1]) <= gap_tol:
            result.append((pts, idxs + [None], True))
        else:
            result.append((pts, idxs, False))
    return result


def order_segments(segments, tol=TOLERANCE_FT,
                   gap_tol=GAP_TOL_FT,
                   collinear_offset=COLLINEAR_OFFSET_FT):
    """Unordered segments -> connected chains, bridging real-model gaps.

    Returns list of (points, seg_indices, closed); seg_indices[k] is the
    input index of the segment between points[k] and points[k+1]
    (wrapping for closed chains) - None for bridged connectors.
    """
    if not segments:
        return []
    return _merge_chains(_exact_chains(segments, tol),
                         gap_tol, collinear_offset)


# ------------------------------------------------------------ splitting

def _segment_axes(pts, idxs, closed):
    """Axis per segment: 'x', 'y', or 'micro' for short segments whose
    neighbors disagree. Short segments (< RECT_MIN_SEG_FT) inherit the
    shared axis of their neighbors - an offset-bump connector between
    two collinear-ish pieces stays inside their run as a jog."""
    n_seg = len(idxs)
    axes = []
    for k in range(n_seg):
        a = pts[k]
        b = pts[0] if (closed and k == n_seg - 1) else pts[k + 1]
        dx = abs(b[0] - a[0])
        dy = abs(b[1] - a[1])
        if (dx * dx + dy * dy) ** 0.5 < RECT_MIN_SEG_FT:
            axes.append(None)
        else:
            axes.append("x" if dx >= dy else "y")

    for k in range(n_seg):
        if axes[k] is None:
            if closed:
                prev_axis = axes[(k - 1) % n_seg]
                next_axis = axes[(k + 1) % n_seg]
            else:
                prev_axis = axes[k - 1] if k > 0 else None
                next_axis = axes[k + 1] if k < n_seg - 1 else None
            if prev_axis is not None and prev_axis == next_axis:
                axes[k] = prev_axis
            else:
                axes[k] = "micro"
    return axes


def split_runs(pts, idxs, closed):
    """Split a chain into maximal single-axis runs.

    Returns list of (run_points, run_seg_indices); indices may contain
    None for bridged connectors. Runs made ONLY of bridged connectors
    (no real wall) are dropped - their endpoints already bound the
    neighboring runs. Direction grouping downstream reassembles runs
    into per-facing catch-all strings, so fragmenting here is fine and
    keeps every run strictly one-directional (the old "side" grouping
    failed live on a 3.7 ft x 7 ft bump-out)."""
    if len(pts) < 2:
        raise GeometryError("Wall run needs at least 2 points")
    if len(idxs) == 0:
        raise GeometryError("Wall run has no segments")

    axes = _segment_axes(pts, idxs, closed)
    n_seg = len(idxs)

    if closed:
        start = None
        for k in range(n_seg):
            if axes[k] != axes[k - 1]:
                start = k
                break
        if start is None:
            raise GeometryError(
                "Exterior loop runs in a single direction - invalid loop")
        pts_open = pts[start:] + pts[:start] + [pts[start]]
        idxs_open = idxs[start:] + idxs[:start]
        return split_runs(pts_open, idxs_open, False)

    runs = []
    k0 = 0
    for k in range(1, n_seg + 1):
        if k == n_seg or axes[k] != axes[k0]:
            run_idxs = idxs[k0:k]
            has_real_wall = False
            for i in run_idxs:
                if i is not None:
                    has_real_wall = True
                    break
            if has_real_wall:
                runs.append((pts[k0:k + 1], run_idxs))
            k0 = k
    return runs


# ----------------------------------------------------------- tier math

def dominant_axis(polyline):
    xs = [p[0] for p in polyline]
    ys = [p[1] for p in polyline]
    return "x" if (max(xs) - min(xs)) >= (max(ys) - min(ys)) else "y"


def is_rectilinear(polyline, angle_tol_deg=ANGLE_TOL_DEG,
                   min_seg_ft=RECT_MIN_SEG_FT):
    """True if every segment >= min_seg_ft is axis-aligned within
    angle_tol_deg (short gap-bridge connectors may be diagonal)."""
    for i in range(len(polyline) - 1):
        dx = polyline[i + 1][0] - polyline[i][0]
        dy = polyline[i + 1][1] - polyline[i][1]
        if (dx * dx + dy * dy) ** 0.5 < min_seg_ft:
            continue
        angle = math.degrees(math.atan2(abs(dy), abs(dx)))
        if angle_tol_deg < angle < (90.0 - angle_tol_deg):
            return False
    return True


def find_jog_points(polyline, angle_tol_deg=ANGLE_TOL_DEG):
    """Direction-change points plus both endpoints."""
    if len(polyline) < 2:
        raise GeometryError("Wall run needs at least 2 points")
    if len(polyline) == 2:
        return [polyline[0], polyline[1]]
    jogs = [polyline[0]]
    for v in range(1, len(polyline) - 1):
        if _is_turn(polyline[v - 1], polyline[v], polyline[v + 1],
                    angle_tol_deg):
            jogs.append(polyline[v])
    jogs.append(polyline[-1])
    return jogs


def stab_positions(intervals):
    """Minimal set of positions such that every [lo, hi] interval
    contains at least one (classic greedy interval stabbing - sort by
    upper bound, place a point at the upper bound of the first
    uncovered interval). Used to choose interior dimension scan lines:
    one position per band of rooms. Degenerate intervals (hi < lo)
    are skipped."""
    usable = [iv for iv in intervals if iv[1] >= iv[0]]
    usable.sort(key=lambda iv: iv[1])
    out = []
    for lo, hi in usable:
        if not out or lo > out[-1]:
            out.append(hi)
    return out


def point_segment_distance(pt, a, b):
    """2D distance from point pt to segment a-b."""
    ax, ay = a
    bx, by = b
    px, py = pt
    dx = bx - ax
    dy = by - ay
    seg_len_sq = dx * dx + dy * dy
    if seg_len_sq == 0:
        return _dist(pt, a)
    t = ((px - ax) * dx + (py - ay) * dy) / seg_len_sq
    t = max(0.0, min(1.0, t))
    return _dist(pt, (ax + t * dx, ay + t * dy))


def distance_to_polyline(pt, polyline):
    """Min 2D distance from pt to any segment of the polyline."""
    best = None
    for i in range(len(polyline) - 1):
        d = point_segment_distance(pt, polyline[i], polyline[i + 1])
        if best is None or d < best:
            best = d
    return best


def project_onto_axis(points, axis, tol=TOLERANCE_FT):
    idx = 0 if axis == "x" else 1
    out = []
    for v in sorted(p[idx] for p in points):
        if not out or abs(v - out[-1]) > tol:
            out.append(v)
    return out


def build_tiers(polyline, opening_points,
                angle_tol_deg=ANGLE_TOL_DEG,
                tol=TIER_MERGE_TOL_FT):
    """The exterior_wall_dimension_string rule for ONE single-axis run.

    Returns {'axis', 'tier1', 'tier2', 'tier3'}:
      tier1 - jogs + opening centerlines (closest to the wall)
      tier2 - jogs only
      tier3 - overall run, end to end (outermost)

    (split_runs guarantees single-axis runs, so the old two-directions
    guard is gone - it fired live on a legitimate bump-out and killed a
    whole building side.)
    """
    if not is_rectilinear(polyline, angle_tol_deg):
        raise NotRectilinearError(
            "Run contains an angled or curved segment - out of scope "
            "for v1, dimension manually")

    axis = dominant_axis(polyline)
    jogs = find_jog_points(polyline, angle_tol_deg)
    return {
        "axis": axis,
        "tier1": project_onto_axis(jogs + list(opening_points), axis, tol),
        "tier2": project_onto_axis(jogs, axis, tol),
        "tier3": project_onto_axis([polyline[0], polyline[-1]], axis, tol),
    }


# ------------------------------------------------ room polygons (interior)
#
# A room is a CLOSED polygon of boundary points, in order, WITHOUT a
# repeated last point. Edge k runs from poly[k] to poly[(k+1) % len(poly)],
# so an edge index maps 1:1 back to the Revit BoundarySegment that produced
# it - that is what lets an interior dimension bind to the wall that really
# bounds the room instead of the nearest wall it can find.


def polygon_bounds(poly):
    """((min_x, min_y), (max_x, max_y)) of a room polygon."""
    if not poly:
        raise GeometryError("Empty room polygon")
    xs = [p[0] for p in poly]
    ys = [p[1] for p in poly]
    return (min(xs), min(ys)), (max(xs), max(ys))


def point_in_polygon(pt, poly):
    """True if pt is inside the polygon (even-odd ray casting). Used to
    assign a fixture/casework instance to the room that contains it.
    Points exactly on an edge are not guaranteed either way - fixtures
    sit well inside a room, so this is not worth the extra cost."""
    if len(poly) < 3:
        return False
    x, y = pt
    inside = False
    n = len(poly)
    for k in range(n):
        ax, ay = poly[k]
        bx, by = poly[(k + 1) % n]
        # half-open rule (ay <= y < by): a vertex is counted once, never
        # twice, so a ray grazing a corner does not flip `inside` twice
        if (ay > y) != (by > y):
            t = (y - ay) / (by - ay)
            if x < ax + t * (bx - ax):
                inside = not inside
    return inside


def polygon_crossings(poly, axis, perp):
    """Where a scan line crosses the room's boundary.

    axis 'x' = the line runs east-west at y=perp; axis 'y' = it runs
    north-south at x=perp. Returns [(value, edge_index)] sorted by value,
    where `value` is the coordinate ALONG the axis and `edge_index` is the
    polygon edge (hence the wall) that produced the crossing.

    Edges parallel to the scan line produce no crossing (the half-open
    test skips them) - a wall parallel to the string is not one of its
    ends, it is what the string runs alongside."""
    idx = 0 if axis == "x" else 1
    pidx = 1 - idx
    hits = []
    n = len(poly)
    for k in range(n):
        a = poly[k]
        b = poly[(k + 1) % n]
        if (a[pidx] > perp) == (b[pidx] > perp):
            continue  # both ends the same side of the line (or parallel)
        t = (perp - a[pidx]) / (b[pidx] - a[pidx])
        hits.append((a[idx] + t * (b[idx] - a[idx]), k))
    hits.sort()
    return hits


def polygon_span_at(poly, axis, perp):
    """The room's INTERIOR extent along `axis` at scan position `perp`:
    ((lo_value, lo_edge), (hi_value, hi_edge)), or None when the line
    misses the room.

    Crossings pair up (0,1), (2,3), ... into interior intervals - a
    U-shaped room cut through both legs gives two. The LONGEST interval
    wins: it is the room's real extent at that line, and its two edges are
    the two walls the dimension may reference. Everything else in interior
    mode is downstream of this - a string can only ever bind to the two
    walls this returns, which is what makes 'never go through a wall'
    structural rather than a heuristic."""
    hits = polygon_crossings(poly, axis, perp)
    best = None
    for k in range(0, len(hits) - 1, 2):
        lo, hi = hits[k], hits[k + 1]
        if best is None or (hi[0] - lo[0]) > (best[1][0] - best[0][0]):
            best = (lo, hi)
    if best is None or (best[1][0] - best[0][0]) <= 0:
        return None
    return best


def outermost_index(items, chosen, window_ft=0.5):
    """Index of the outermost face on the SAME wall and SAME side as
    `chosen`. Pure decision logic behind revit_io.outermost_same_face.

    items: [(wall_key, coord_along_axis, normal_along_axis)], chosen: index.

    A wall solid can present several faces on one side, a fraction of an
    inch apart (the finish layer, and what sits behind it). Picking a face
    by distance-to-target lands on the NEARER one - one step INSIDE the
    finish face, which is the live-reported exterior defect. This walks
    outward, along the chosen face's own normal, to the last face of that
    same wall on that same side.

    It can only ever return a face with the same wall_key and the same
    normal sign as `chosen`, so it cannot change which wall or which side
    was picked - a wall exposing one face per side is a no-op."""
    key, coord, normal = items[chosen]
    if normal == 0:
        return chosen
    outward = 1.0 if normal > 0 else -1.0
    base = coord * outward

    best = chosen
    best_out = base
    for i in range(len(items)):
        k, c, n = items[i]
        if k != key or n * normal <= 0:
            continue
        reach = c * outward
        if reach <= best_out or (reach - base) > window_ft:
            continue
        best_out = reach
        best = i
    return best


def quarter_lines(poly, axis):
    """The two candidate positions for a room-length string: a quarter of
    the room's depth in from each parallel wall (user rule). axis 'x' =>
    two y positions. Caller picks whichever is least obstructed."""
    (min_x, min_y), (max_x, max_y) = polygon_bounds(poly)
    if axis == "x":
        lo, hi = min_y, max_y
    else:
        lo, hi = min_x, max_x
    depth = hi - lo
    return [lo + 0.25 * depth, hi - 0.25 * depth]


# --------------------------------------- exterior placement (offsets)


def tier_positions(base, side, first_ft, step_ft, count):
    """Perpendicular positions of the stacked exterior tiers: the first
    string sits first_ft off the base, each further tier step_ft beyond.
    With first_ft == step_ft this reproduces the legacy base + N*step
    stack exactly (back-compat identity, unit-tested)."""
    return [base + side * (first_ft + i * step_ft) for i in range(count)]


def snap_base_outward(base, side, face_perps, max_shift_ft=2.0):
    """Move the placement base from the location-line extreme OUT to the
    wall's real face plane, never inward.

    base comes from location-line points, but witness lines run to finish
    faces which can sit up to a full wall thickness beyond (depends on
    each wall's Location Line setting - so this is MEASURED from the
    faces, never guessed from Wall.Width). face_perps are the
    perpendicular coordinates of the run walls' exterior long faces;
    the outermost one in the `side` direction wins, clamped to
    max_shift_ft so a distant stray face cannot yank the string away."""
    if not face_perps:
        return base
    candidate = face_perps[0]
    for p in face_perps:
        if (p - candidate) * side > 0:
            candidate = p
    shift = (candidate - base) * side
    if shift <= 0 or shift > max_shift_ft:
        return base
    return candidate


# ----------------------------- exterior direction-group clustering
#
# One string set per facing direction (v3.4, image-confirmed) is right
# for a single building mass - and wrong for a large plan with several
# masses/wings, where it drags witness lines clean across the plan into
# one far-away string (live report: "a mess of crossed lines"). The rule
# that separates the two cases is the user's own phrasing: a dimension's
# witness lines must not CROSS a wall. A run only joins a farther
# cluster when every witness line it would extend to that cluster's
# base travels through open space.


def witness_crosses(value, perp_from, perp_to, axis, segments,
                    end_tol=WITNESS_END_TOL_FT,
                    val_tol=TIER_MERGE_TOL_FT):
    """True when the witness line at `value` (a coordinate ALONG `axis`),
    extended perpendicular from perp_from to perp_to, transversely
    crosses any of the wall segments.

    A segment only counts when the witness's value lies STRICTLY inside
    the segment's along-axis extent (an endpoint touch is a shared jog
    corner, not a crossing), and the intersection sits strictly inside
    the witness span minus end_tol at both ends (walls at either end of
    the witness are its own anchors, not obstructions). Segments running
    parallel to the witness never cross - drafters run witness lines
    alongside walls constantly."""
    idx = 0 if axis == "x" else 1
    pidx = 1 - idx
    lo = min(perp_from, perp_to) + end_tol
    hi = max(perp_from, perp_to) - end_tol
    if lo >= hi:
        return False
    for a, b in segments:
        a_along = a[idx]
        b_along = b[idx]
        if abs(b_along - a_along) < 1e-9:
            continue  # parallel to the witness direction
        s_lo = min(a_along, b_along)
        s_hi = max(a_along, b_along)
        if not (s_lo + val_tol < value < s_hi - val_tol):
            continue  # outside, or an endpoint touch (shared corner)
        t = (value - a_along) / (b_along - a_along)
        perp_at = a[pidx] + t * (b[pidx] - a[pidx])
        if lo < perp_at < hi:
            return True
    return False


def cluster_exterior_runs(records, segments, axis, side, max_drag_ft=0.0):
    """Split one (axis, side) direction bucket into clusters whose
    witness lines never cross a wall.

    records: [(perp_extreme, witness_values), ...] - one per run;
    perp_extreme is the run's own outermost perpendicular coordinate in
    the `side` direction, witness_values its tier-1 values (jogs +
    openings - exactly where witness lines will stand).
    segments: frame-local wall segments of the SAME selection and frame
    (only selected walls may block a merge).
    max_drag_ft: optional extra rule - 0 disables it; otherwise a run
    whose face would sit farther than this behind the cluster's base
    starts its own cluster even without a crossing.

    Runs are visited outermost first, so a cluster's base is fixed by
    its first member and membership can never invalidate retroactively.
    Returns a list of clusters, each a list of record indices, in
    outermost-first creation order. With one mass and no crossings this
    returns a single cluster = exact v3.4 behavior."""
    order = sorted(range(len(records)),
                   key=lambda i: -side * records[i][0])
    clusters = []  # [{"base": float, "members": [record index]}]
    for i in order:
        perp_extreme, witness_values = records[i]
        joined = False
        for cluster in clusters:
            if max_drag_ft > 0.0:
                drag = (cluster["base"] - perp_extreme) * side
                if drag > max_drag_ft:
                    continue
            blocked = False
            for v in witness_values:
                if witness_crosses(v, perp_extreme, cluster["base"],
                                   axis, segments):
                    blocked = True
                    break
            if not blocked:
                cluster["members"].append(i)
                joined = True
                break
        if not joined:
            clusters.append({"base": perp_extreme, "members": [i]})
    return [c["members"] for c in clusters]
