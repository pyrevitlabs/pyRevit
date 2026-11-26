# -*- coding: utf-8 -*-
"""Ordering rules of a plan view range. Nothing here imports Revit.

``preview.js`` applies the same order while a plane is dragged.

Invariant:
    Plans that look down keep Top >= Cut >= Bottom >= View Depth. Reflected
    ceiling plans look up and keep View Depth >= Top >= Cut. Their Bottom is
    not shown or edited, but Revit does not move it with the cut plane and
    rejects a cut plane below it, so it must be written along with the cut
    plane.

    A plane set to Unlimited has no elevation and limits no other plane.
"""

TOP = "top"
CUT = "cut"
BOTTOM = "bottom"
DEPTH = "depth"

DOWNWARD_ORDER = (TOP, CUT, BOTTOM, DEPTH)
CEILING_ORDER = (DEPTH, TOP, CUT)
ORDER_TOLERANCE_FT = 1e-6
ALIGNED_DEPTH_MARGIN_FT = 3.0


def plane_order(ceiling):
    """Return the editable planes from the highest to the lowest."""
    return CEILING_ORDER if ceiling else DOWNWARD_ORDER


def find_order_violation(elevations, ceiling):
    """Return the first pair of planes that is out of order.

    Args:
        elevations (dict): plane id -> elevation in feet; Unlimited planes are
            absent or None.
        ceiling (bool): the view is a reflected ceiling plan.

    Returns:
        tuple[str, str] | None: ``(higher, lower)`` ids where the plane that
        must be higher lies below the other, or None when the order holds.
    """
    present = [p for p in plane_order(ceiling) if elevations.get(p) is not None]
    for higher, lower in zip(present, present[1:]):
        if elevations[higher] < elevations[lower] - ORDER_TOLERANCE_FT:
            return higher, lower
    return None


def aligned_elevations(low, high, ceiling):
    """Return the view range that shows the vertical extent ``low`` to ``high``.

    The cut plane sits in the middle and the view depth reaches
    ``ALIGNED_DEPTH_MARGIN_FT`` past the far end of the range, which is below
    ``low`` for plans that look down and above ``high`` for ceiling plans.
    """
    cut = (low + high) / 2.0
    if ceiling:
        return {TOP: high, CUT: cut, DEPTH: high + ALIGNED_DEPTH_MARGIN_FT}
    return {TOP: high, CUT: cut, BOTTOM: low, DEPTH: low - ALIGNED_DEPTH_MARGIN_FT}
