# -*- coding: utf-8 -*-
"""Validation of the 3D preview's remembered display and box settings.

The page posts its toggles, cut mode and ghost strength; the navigator keeps
them as one JSON string in its config and hands them back when the preview
mounts. Neither side trusts the other: unknown keys and values of the wrong
type are dropped, so a stale or hand-edited config cannot break the page.
Nothing here imports Revit.
"""

import json

FLAG_KEYS = ("model", "levels", "allLevels", "grids", "names", "scope", "live", "snap")
CUT_MODES = ("ghost", "hide", "off")
GHOST_MIN = 0.02
GHOST_MAX = 0.6
SIDE_WIDTH_MIN = 160.0
SIDE_WIDTH_MAX = 1200.0


def _number_in(value, low, high):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if value != value:
        return None
    return min(high, max(low, float(value)))


def clean_settings(data):
    """Return the valid entries of ``data``: boolean flags, ``cut``, ``ghost`` and ``sideWidth``.

    ``ghost`` is clamped to the range the page's slider offers and
    ``sideWidth`` (the category panel's width in pixels) to its limits.
    """
    clean = {}
    if not isinstance(data, dict):
        return clean
    for key in FLAG_KEYS:
        if isinstance(data.get(key), bool):
            clean[key] = data[key]
    if data.get("cut") in CUT_MODES:
        clean["cut"] = data["cut"]
    ghost = _number_in(data.get("ghost"), GHOST_MIN, GHOST_MAX)
    if ghost is not None:
        clean["ghost"] = ghost
    side_width = _number_in(data.get("sideWidth"), SIDE_WIDTH_MIN, SIDE_WIDTH_MAX)
    if side_width is not None:
        clean["sideWidth"] = side_width
    return clean


def parse_settings(text):
    """Return the settings stored in JSON ``text``, empty when it is missing or broken.

    The config reader turns a hand-edited ``true`` or ``{}`` into a bool or
    dict rather than text, so anything but a string counts as broken too.
    """
    try:
        return clean_settings(json.loads(text)) if text else {}
    except (TypeError, ValueError):
        return {}


def dump_settings(data):
    """Return ``data`` cleaned and encoded as the JSON string kept in the config."""
    return json.dumps(clean_settings(data), sort_keys=True)
