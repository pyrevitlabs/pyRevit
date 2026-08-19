"""Geometric utilities for Revit."""

from pyrevit import DB
from pyrevit.framework import clr
from pyrevit.compat import IRONPY


def intersect_curves(curve1, curve2):
    """
    Intersects two curves on any engine.

    Wraps Curve.Intersect's out-param, which needs engine-specific
    marshaling: an explicit clr.Reference under IronPython, a return tuple
    under CPython/pythonnet.

    Args:
        curve1 (DB.Curve): first curve
        curve2 (DB.Curve): second curve

    Returns:
        (tuple[DB.SetComparisonResult, DB.IntersectionResultArray]):
            comparison result, and the intersection results (None when the
            curves do not intersect).
    """
    if IRONPY:
        results = clr.Reference[DB.IntersectionResultArray]()
        intres = curve1.Intersect(curve2, results)
        return intres, results.Value
    return curve1.Intersect(curve2, None)


def convert_point_coord_system(rvt_point, rvt_transform):
    """Return coordinates of point in another coordinate system.

    Args:
        rvt_point (DB.XYZ): Revit point
        rvt_transform (DB.Transform): Revit transform for target coord system

    Returns:
        (DB.XYZ): Point coordinates in new coordinate system.
    """
    # transform the origin of the old coordinate system in the new
    # coordinate system
    return rvt_transform.OfVector(rvt_transform.Origin - rvt_point)


def convert_point_to_metric(rvt_point):
    """Convert given point coordinates to metric."""
    return DB.XYZ(rvt_point.X * 0.3048,
                  rvt_point.Y * 0.3048,
                  rvt_point.Z * 0.3048)
