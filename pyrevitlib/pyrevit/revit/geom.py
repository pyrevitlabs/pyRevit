"""Geometric utilities for Revit."""

from pyrevit import DB


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
