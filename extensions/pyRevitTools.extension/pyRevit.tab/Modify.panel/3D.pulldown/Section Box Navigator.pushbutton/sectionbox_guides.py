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


def _distance_to_line(line, x, y):
    lx, ly, dx, dy = line
    return abs((x - lx) * dy - (y - ly) * dx)


def _end_points(entry):
    x1, y1, x2, y2 = entry["segs"][0]
    return ((x1, y1), (x2, y2))


def _repeats(entry, other):
    line, other_line = _straight_line(entry), _straight_line(other)
    if line is None or other_line is None:
        return False
    if abs(line[2] * other_line[3] - line[3] * other_line[2]) > GRID_PARALLEL_SIN:
        return False
    limit = GRID_SAME_NAME_FT if entry["name"] == other["name"] else GRID_COLLINEAR_FT
    ends = [(point, line) for point in _end_points(other)]
    ends += [(point, other_line) for point in _end_points(entry)]
    return all(_distance_to_line(ref, *point) <= limit for point, ref in ends)


def drop_repeated_grids(entries):
    """Return ``entries`` without linked straight grids on an already listed line.

    Args:
        entries (list[dict]): ``{name, link, segs}`` entries.

    A linked grid repeats a listed one when the two are parallel within half a
    degree and both end points of each lie less than ``GRID_COLLINEAR_FT`` from
    the other's line, or less than ``GRID_SAME_NAME_FT`` when they carry the
    same name. Checking the ends keeps a long grid that drifts away at a small
    angle from counting as a repeat. Host grids are
    always kept and curved grids are never compared. The order is unchanged.
    """
    kept = [entry for entry in entries if not entry["link"]]
    for entry in entries:
        if entry["link"] and not any(_repeats(entry, other) for other in kept):
            kept.append(entry)
    kept_ids = set(id(entry) for entry in kept)
    return [entry for entry in entries if id(entry) in kept_ids]
