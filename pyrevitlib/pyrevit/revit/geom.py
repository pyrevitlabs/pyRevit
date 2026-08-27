"""Geometric utilities for Revit."""

from pyrevit import DB
from pyrevit.framework import clr
from pyrevit.compat import IRONPY


def _extract_intersection_points(results_array):
    """Return intersection XYZ points from an IntersectionResultArray.

    Args:
        results_array (DB.IntersectionResultArray): intersection results

    Returns:
        (list[DB.XYZ] | None): intersection points, or None when the
            curves do not intersect.
    """
    if not results_array:
        return None
    return [result.XYZPoint for result in results_array]


def intersect_curves(curve1, curve2):
    """Intersects two curves on any engine and host API generation.

    Hosts still shipping the ``Curve.Intersect(Curve, ref array)`` overload
    marshal the out-param engine-specifically (explicit ``clr.Reference``
    under IronPython, direct tuple under CPython/pythonnet). Revit 2026+
    removed that overload in favor of ``Curve.Intersect(Curve,
    CurveIntersectResultOption)``, detected here by ``TypeError`` fallback.

    Args:
        curve1 (DB.Curve): first curve
        curve2 (DB.Curve): second curve

    Returns:
        (tuple[DB.SetComparisonResult, list[DB.XYZ] | None]):
            comparison result, and the intersection points (None when the
            curves do not intersect).
    """
    if IRONPY:
        results = clr.Reference[DB.IntersectionResultArray]()
        try:
            intres = curve1.Intersect(curve2, results)
            return intres, _extract_intersection_points(results.Value)
        except TypeError:
            pass
    else:
        try:
            intres, results = curve1.Intersect(curve2, None)
            return intres, _extract_intersection_points(results)
        except (TypeError, ValueError):
            pass
    intersect_result = curve1.Intersect(curve2, DB.CurveIntersectResultOption.Detailed)
    overlap_items = list(intersect_result.GetOverlaps() or [])
    points = [overlap.Point for overlap in overlap_items] if overlap_items else None
    return intersect_result.Result, points


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
    return DB.XYZ(rvt_point.X * 0.3048, rvt_point.Y * 0.3048, rvt_point.Z * 0.3048)
