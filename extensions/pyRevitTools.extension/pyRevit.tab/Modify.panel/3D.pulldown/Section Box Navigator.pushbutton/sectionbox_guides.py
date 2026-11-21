# -*- coding: utf-8 -*-
"""Collapse the levels and grids of linked models that repeat the host's.

Revit keeps no identity between a level or grid of a link and the one it was
copied from, apart from Copy/Monitor relationships that most models never set
up. The preview therefore compares geometry in host coordinates: a linked level
at the elevation of a listed one, or a linked grid on the line of a listed one,
adds a second label for the same snap target and is left out.

The functions work on the payload entries built by ``sectionbox_scene``
(``levels_payload`` and ``grids_payload``) and import nothing from Revit.
"""

import math

LEVEL_TOLERANCE_FT = 0.01
GRID_COLLINEAR_FT = 0.05
GRID_SAME_NAME_FT = 1.0
GRID_PARALLEL_SIN = math.sin(math.radians(0.5))


def drop_repeated_levels(entries):
    """Return ``entries`` without linked levels at an already listed elevation.

    Args:
        entries (list[dict]): ``{name, z, elevation, link}`` entries.

    Host levels are always kept, so a linked level never replaces a host one,
    and a linked level repeating another linked level keeps the first.
    Elevations closer than ``LEVEL_TOLERANCE_FT`` count as equal. The result is
    sorted by ``z``.
    """
    kept = [entry for entry in entries if not entry["link"]]
    for entry in entries:
        if entry["link"] and not any(
            abs(entry["z"] - other["z"]) <= LEVEL_TOLERANCE_FT for other in kept
        ):
            kept.append(entry)
    return sorted(kept, key=lambda entry: entry["z"])


def _straight_line(entry):
    segments = entry["segs"]
    if len(segments) != 1:
        return None
    x1, y1, x2, y2 = segments[0]
    length = math.hypot(x2 - x1, y2 - y1)
    if length < 1e-9:
        return None
    return x1, y1, (x2 - x1) / length, (y2 - y1) / length


def _repeats(entry, other):
    line, other_line = _straight_line(entry), _straight_line(other)
    if line is None or other_line is None:
        return False
    x, y, dx, dy = line
    ox, oy, odx, ody = other_line
    if abs(dx * ody - dy * odx) > GRID_PARALLEL_SIN:
        return False
    gap = abs((ox - x) * dy - (oy - y) * dx)
    limit = GRID_SAME_NAME_FT if entry["name"] == other["name"] else GRID_COLLINEAR_FT
    return gap <= limit


def drop_repeated_grids(entries):
    """Return ``entries`` without linked straight grids on an already listed line.

    Args:
        entries (list[dict]): ``{name, link, segs}`` entries.

    A linked grid repeats a listed one when the two are parallel within half a
    degree and less than ``GRID_COLLINEAR_FT`` apart, or less than
    ``GRID_SAME_NAME_FT`` apart when they carry the same name. Host grids are
    always kept and curved grids are never compared. The order is unchanged.
    """
    kept = [entry for entry in entries if not entry["link"]]
    for entry in entries:
        if entry["link"] and not any(_repeats(entry, other) for other in kept):
            kept.append(entry)
    kept_ids = set(id(entry) for entry in kept)
    return [entry for entry in entries if id(entry) in kept_ids]
