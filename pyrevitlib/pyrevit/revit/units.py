"""Unit conversion utilities for Revit."""

from pyrevit import HOST_APP
from pyrevit import DB


def format_area(area_value, doc=None):
    """Return formatted area value in document units.

    Args:
        area_value (float): area value
        doc (DB.Document, optional): Revit document, defaults to current

    Returns:
        str: formatted value
    """
    doc = doc or HOST_APP.doc
    return DB.UnitFormatUtils.Format(units=doc.GetUnits(),
                                     unitType=DB.UnitType.UT_Area,
                                     value=area_value,
                                     maxAccuracy=False,
                                     forEditing=False)


def format_slope(slope_value, doc=None):
    """Return formatted slope value in document units.

    Args:
        slope_value (float): slope value
        doc (DB.Document, optional): Revit document, defaults to current

    Returns:
        str: formatted value
    """
    doc = doc or HOST_APP.doc
    return DB.UnitFormatUtils.Format(units=doc.GetUnits(),
                                     unitType=DB.UnitType.UT_Slope,
                                     value=slope_value,
                                     maxAccuracy=False,
                                     forEditing=False)


def _create_view_plane(view):
    """Get a plane parallel to a view

    Args:
        view (DB.View): view to align plane

    Returns:
        DB.Plane: result plane
    """
    return DB.Plane.CreateByOriginAndBasis(
        view.Origin, view.RightDirection, view.UpDirection)


def project_to_viewport(xyz, view):
    """Project a point to viewport coordinates

    Args:
        xyz (DB.XYZ): point to project
        view (DB.View): target view

    Returns:
        DB.UV: [description]
    """
    plane = _create_view_plane(view)
    uv, _ = plane.Project(xyz)
    return uv


def project_to_world(uv, view):
    """Get view-based point (UV) back to model coordinates.

    Args:
        uv (DB.UV): point on a view
        view (DB.View): view to get coordinates from

    Returns:
        DB.XYZ: point in world coordinates
    """
    plane = _create_view_plane(view)
    trf = DB.Transform.Identity
    trf.BasisX = plane.XVec
    trf.BasisY = plane.YVec
    trf.BasisZ = plane.Normal
    trf.Origin = plane.Origin
    return trf.OfPoint(DB.XYZ(uv.U, uv.V, 0))
