# -*- coding: utf-8 -*-
"""Read and edit the view range of a plan view.

Important:
    Only plane offsets are written, so every plane keeps its associated level.

    Planes set to Unlimited, Level Above or Level Below have no elevation here.
    The API does not report which level Revit resolves the last two to, and a
    guess would write a wrong offset.

    Revit accepts ``SetViewRange`` on a view whose template controls the view
    range, so callers editing on the user's behalf must check
    :func:`controlling_template_name` first.
"""

from pyrevit import DB

from sectionbox_viewrange_rules import (
    BOTTOM,
    CUT,
    DEPTH,
    TOP,
    find_order_violation,
    plane_order,
)

_PLANES = {
    TOP: DB.PlanViewPlane.TopClipPlane,
    CUT: DB.PlanViewPlane.CutPlane,
    BOTTOM: DB.PlanViewPlane.BottomClipPlane,
    DEPTH: DB.PlanViewPlane.ViewDepthPlane,
}
_EDITABLE_VIEW_TYPES = (
    DB.ViewType.FloorPlan,
    DB.ViewType.CeilingPlan,
    DB.ViewType.EngineeringPlan,
)


class ViewRangeError(Exception):
    """A view range edit that must not be written.

    Attributes:
        reason (str): "order" or "unknown_plane".
        planes (tuple[str]): the ``(higher, lower)`` planes that are out of
            order, or the plane that has no elevation.
    """

    def __init__(self, reason, planes):
        Exception.__init__(self, "{}: {}".format(reason, ", ".join(planes)))
        self.reason = reason
        self.planes = tuple(planes)


def has_view_range(view):
    """True for the plan views whose view range the preview shows."""
    return isinstance(view, DB.ViewPlan) and view.ViewType in _EDITABLE_VIEW_TYPES


def is_ceiling_plan(view):
    """True for plans that look up, including structural plans set to do so."""
    return view.ViewType == DB.ViewType.CeilingPlan


def controlling_template_name(view):
    """Return the name of the view template that controls the view range, or None."""
    if view.ViewTemplateId == DB.ElementId.InvalidElementId:
        return None
    template = view.Document.GetElement(view.ViewTemplateId)
    view_range_id = DB.ElementId(DB.BuiltInParameter.PLAN_VIEW_RANGE)
    controlled = view_range_id in list(
        template.GetTemplateParameterIds()
    ) and view_range_id not in list(template.GetNonControlledTemplateParameterIds())
    return template.Name if controlled else None


def _plane_level(view, view_range, plane):
    level_id = view_range.GetLevelId(_PLANES[plane])
    if level_id == DB.PlanViewRange.Current:
        return view.GenLevel
    level = view.Document.GetElement(level_id)
    return level if isinstance(level, DB.Level) else None


def read_planes(view):
    """Return the planes that have an elevation, from the highest to the lowest.

    Returns:
        list[dict]: ``{id, elevation, level, levelElevation}`` with project
        elevations in feet. A ceiling plan lists no Bottom plane.
    """
    view_range = view.GetViewRange()
    planes = []
    for plane in plane_order(is_ceiling_plan(view)):
        level = _plane_level(view, view_range, plane)
        if level is None:
            continue
        planes.append(
            {
                "id": plane,
                "elevation": level.ProjectElevation
                + view_range.GetOffset(_PLANES[plane]),
                "level": level.Name,
                "levelElevation": level.ProjectElevation,
            }
        )
    return planes


def relative_level_planes(view):
    """Return the ids of the planes set to Level Above or Level Below."""
    view_range = view.GetViewRange()
    relative = (DB.PlanViewRange.LevelAbove, DB.PlanViewRange.LevelBelow)
    return [
        plane
        for plane in plane_order(is_ceiling_plan(view))
        if view_range.GetLevelId(_PLANES[plane]) in relative
    ]


def plane_elevations(view):
    """Return ``{plane id: project elevation}`` for the planes that have one."""
    return dict((plane["id"], plane["elevation"]) for plane in read_planes(view))


def build_view_range(view, changes):
    """Return the view's ``DB.PlanViewRange`` with the planes in ``changes`` moved.

    Nothing is written to the view; pass the result to ``SetViewRange`` inside a
    transaction. On a ceiling plan a moved cut plane takes the unused Bottom
    plane along: Revit does not do that itself and rejects a cut plane below it.

    Args:
        view (DB.ViewPlan): plan view.
        changes (dict): plane id -> new project elevation in feet.

    Raises:
        ViewRangeError: a plane has no elevation to move, or the planes would
            be out of order.
    """
    ceiling = is_ceiling_plan(view)
    elevations = plane_elevations(view)
    for plane in changes:
        if plane not in elevations:
            raise ViewRangeError("unknown_plane", (plane,))
    elevations.update(changes)
    violation = find_order_violation(elevations, ceiling)
    if violation:
        raise ViewRangeError("order", violation)
    writes = dict(changes)
    if ceiling and CUT in changes:
        writes[BOTTOM] = changes[CUT]
    view_range = view.GetViewRange()
    for plane, elevation in writes.items():
        level = _plane_level(view, view_range, plane)
        if level is not None:
            view_range.SetOffset(_PLANES[plane], elevation - level.ProjectElevation)
    return view_range


def view_range_payload(view, origin):
    """Describe the view range for the preview page, or None without one.

    Returns:
        dict | None: ``ceiling``, ``template`` (name of the controlling view
        template, which makes the planes read-only), ``relative`` (planes left
        out because they follow the level above or below) and ``planes`` as
        ``{id, z, elevation, level, levelZ}``, ``z`` and ``levelZ`` relative
        to ``origin``.
    """
    if not has_view_range(view):
        return None
    planes = read_planes(view)
    for plane in planes:
        plane["z"] = plane["elevation"] - origin.Z
        plane["levelZ"] = plane.pop("levelElevation") - origin.Z
    return {
        "ceiling": is_ceiling_plan(view),
        "template": controlling_template_name(view),
        "relative": relative_level_planes(view),
        "planes": planes,
    }
