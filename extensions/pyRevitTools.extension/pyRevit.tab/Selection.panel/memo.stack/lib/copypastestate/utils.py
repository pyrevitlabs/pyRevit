"""Copy/Paste State Support Functions"""
#pylint: disable=import-error,invalid-name,broad-except,superfluous-parens
from pyrevit import HOST_APP
from pyrevit import revit, DB


def get_selected_viewports():
    """Extract only viewports from selected elements

    Returns:
        list[DB.Element]: list of viewport elements
    """
    selected_els = revit.get_selection().elements
    return [e for e in selected_els
            if isinstance(e, DB.Viewport)]


def get_selected_views():
    """Extract only views from selected elements

    Returns:
        list[DB.Element]: list of views
    """
    selected_els = revit.get_selection().elements
    return [e for e in selected_els
            if isinstance(e, DB.View)]


def get_views(allow_viewports=True, filter_func=None):
    """Takes either active view or selected view(s) (cropable only)

    Returns:
        list: list of views
    """
    # try to use active view
    # pylint: disable=no-else-return
    if not filter_func or filter_func(revit.active_view):
        return [revit.active_view]
    # try to use selected viewports
    else:
        selected_views = []
        if allow_viewports:
            selected_viewports = get_selected_viewports()
            selected_views.extend([revit.doc.GetElement(viewport.ViewId)
                                   for viewport in selected_viewports])
        selected_views.extend(get_selected_views())
        if filter_func:
            return [view for view in selected_views if filter_func(view)]
        else:
            return selected_views


def get_crop_region(view):
    """Takes crop region of a view

    Args:
        view (DB.View): view to get crop region from

    Returns:
        list[DB.CurveLoop]: list of curve loops
    """
    crsm = view.GetCropRegionShapeManager()
    if HOST_APP.is_newer_than(2015):
        crsm_valid = crsm.CanHaveShape
    else:
        crsm_valid = crsm.Valid

    if crsm_valid:
        if HOST_APP.is_newer_than(2015):
            curve_loops = list(crsm.GetCropShape())
        else:
            curve_loops = [crsm.GetCropRegionShape()]

        if curve_loops:
            return curve_loops


def set_crop_region(view, curve_loops):
    """Sets crop region to a view

    Args:
        view (DB.View): view to change
        curve_loops (list[DB.CurveLoop]): list of curve loops
    """
    if not isinstance(curve_loops, list):
        curve_loops = [curve_loops]

    crop_active_saved = view.CropBoxActive
    view.CropBoxActive = True
    crsm = view.GetCropRegionShapeManager()
    for cloop in curve_loops:
        if HOST_APP.is_newer_than(2015):
            crsm.SetCropShape(cloop)
        else:
            crsm.SetCropRegionShape(cloop)
    view.CropBoxActive = crop_active_saved


def view_plane(view):
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
    plane = view_plane(view)
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
    plane = view_plane(view)
    trf = DB.Transform.Identity
    trf.BasisX = plane.XVec
    trf.BasisY = plane.YVec
    trf.BasisZ = plane.Normal
    trf.Origin = plane.Origin
    return trf.OfPoint(DB.XYZ(uv.U, uv.V, 0))
