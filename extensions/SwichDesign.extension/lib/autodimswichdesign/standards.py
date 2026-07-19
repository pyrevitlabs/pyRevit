# -*- coding: utf-8 -*-
"""US CD dimensioning constants for the Automatic Dimensions rules.

SOURCES: values taken from the user-supplied reference document
("United States CAD and Architectural Dimensioning Standards"), which
summarizes NCS/ANSI conventions. They have NOT been verified against a
licensed primary NCS copy (paywalled). Treat as project defaults, not
certified standard values.

UNITS: Revit's internal length unit is always decimal FEET - every
constant here is feet.

PAPER vs MODEL SPACE: these are PAPER (printed sheet) distances.
For model-space placement multiply by the view scale (View.Scale):
3/8" on paper at 1/8"=1'-0" (scale 96) is 3.0 ft in the model.

IronPython 2.7 note: 1/16 is INTEGER division = 0 there, which would
silently zero these constants - hence the __future__ import and float
literals. Keep both.
"""
from __future__ import division

INCH = 1.0 / 12.0

# Gap between the object and the start of the extension line.
EXTENSION_LINE_GAP_FT = (1.0 / 16.0) * INCH        # 1/16"

# Spacing between stacked/parallel dimension tiers, and minimum
# distance from the object outline to the first dimension line.
TIER_SPACING_FT = (3.0 / 8.0) * INCH               # 3/8"

# --- exterior first-string offset (user-configurable, paper inches) ---
#
# Drafting convention (secondary sources; NCS primary text is paywalled,
# see PROJECT_BRIEF section 1): the FIRST dimension line sits ~1/2" off
# the object, SUBSEQUENT tiers 3/8" apart. The old code used 3/8" for
# both, which put the first string too close to the wall (live report).
# Both values are PAPER inches; multiply by View.Scale for model feet.

TIER_SPACING_DEFAULT_IN = 0.375     # 3/8" between stacked tiers
FIRST_OFFSET_DEFAULT_IN = 0.75      # fallback when scale is unlisted

# "Auto" preset: constant paper offset reads cramped at large scales and
# wasteful at small ones, so the preset tapers with the view scale.
SCALE_FIRST_OFFSET_IN = {
    12: 1.0,     # 1"    = 1'-0"
    16: 1.0,     # 3/4"  = 1'-0"
    24: 0.75,    # 1/2"  = 1'-0"
    32: 0.75,    # 3/8"  = 1'-0"
    48: 0.75,    # 1/4"  = 1'-0"
    64: 0.625,   # 3/16" = 1'-0"
    96: 0.5,     # 1/8"  = 1'-0"
}


def first_offset_for_scale(scale):
    """Preset first-string offset (paper inches) for a view scale.
    Exact table hit, else the nearest listed scale, else the default."""
    if scale in SCALE_FIRST_OFFSET_IN:
        return SCALE_FIRST_OFFSET_IN[scale]
    best = None
    best_d = None
    for key in SCALE_FIRST_OFFSET_IN:
        d = abs(key - scale)
        if best_d is None or d < best_d:
            best_d = d
            best = key
    if best is None:
        return FIRST_OFFSET_DEFAULT_IN
    return SCALE_FIRST_OFFSET_IN[best]


def parse_paper_inches(text):
    """User-typed paper distance -> float inches, or None.

    Accepts '0.75', '3/4', '3/4"', '1 1/2"', '1-1/2'. Anything else
    (including the 'Auto (by view scale)' combo entry) returns None -
    the caller decides what None means."""
    if text is None:
        return None
    s = str(text).strip().replace('"', '').replace("''", '')
    if not s:
        return None
    s = s.replace('-', ' ')
    parts = s.split()
    total = 0.0
    seen = False
    for part in parts:
        if '/' in part:
            top_bot = part.split('/')
            if len(top_bot) != 2:
                return None
            try:
                total += float(top_bot[0]) / float(top_bot[1])
                seen = True
            except (ValueError, ZeroDivisionError):
                return None
        else:
            try:
                total += float(part)
                seen = True
            except ValueError:
                return None
    return total if seen else None

# Minimum overall extension line length.
MIN_EXTENSION_LINE_FT = (9.0 / 16.0) * INCH        # 9/16"

# Minimum plotted text height for dimensions/annotation.
MIN_TEXT_HEIGHT_FT = (3.0 / 32.0) * INCH           # 3/32"

# Exterior dimensioning targets: structural stud faces at run ends,
# centerlines of door/window openings. (Informational - enforced by
# which references revit_io functions return.)
EXTERIOR_TARGET = "stud_face_to_opening_centerline"

# Terminator per US architectural practice is the oblique tick, but the
# actual terminator comes from the DimensionType the user has active -
# not enforced in code.
TERMINATOR = "tick"

# Opening dimensioning modes (user-selectable per run of the tool):
# 'center' - dimension to the opening centerline (classic exterior practice)
# 'ro'     - dimension to both sides of the opening via the family's
#            Left/Right references (rough-opening style; the exact plane
#            depends on how the family's width references were built)
OPENING_MODE_CENTER = "center"
OPENING_MODE_RO = "ro"


def format_ft_in(value_ft):
    """Decimal feet -> readable feet-inches string.

    Normalizes the inches component so 34.9967 ft renders as 35'-0.0",
    never 34'-12.0" (live-observed rounding bug).
    """
    sign = "-" if value_ft < 0 else ""
    total_in = abs(value_ft) * 12.0
    feet = int(total_in // 12)
    inches = total_in - feet * 12
    if inches >= 11.95:
        feet += 1
        inches = 0.0
    return "{0}{1}'-{2:.1f}\"".format(sign, feet, inches)
