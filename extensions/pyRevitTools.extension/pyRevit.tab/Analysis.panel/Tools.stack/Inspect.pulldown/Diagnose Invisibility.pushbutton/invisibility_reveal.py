# -*- coding: utf-8 -*-
"""Reveal-hidden overlay: draw what a view hides, colored by the reason.

Revit's own Reveal Hidden Elements shows only what the Hide command hid. This
overlay runs the same checks as the report on every element in the screen
area of one view and draws the hidden ones through a DirectContext3D server
(``pyrevit.revit.dc3dserver``), one color per reason. It never changes the
model.

Cost is bounded on purpose: candidates come from a bounding-box filter on the
zoomed screen area, tiny elements are skipped, a time budget stops the
diagnosis, and only the largest elements are drawn as solids (the rest as
boxes). The summary reports what was left out.

Warning:
    The server is registered with Revit's DirectContext3D service and the
    optional follow mode hooks ``Idling``. Both stay until
    ``RevealPreview.close`` runs, in Revit API context. The report closes the
    preview when its output window closes.
"""

import time

from pyrevit import DB, HOST_APP
from pyrevit.coreutils.logger import get_logger
from pyrevit.revit import dc3dserver

from invisibility_checks import collect_visible_ids, diagnose, id_value
from invisibility_ghost import element_meshes

logger = get_logger(__name__)

SUPPORTED_VIEW_TYPES = (
    DB.ViewType.ThreeD,
    DB.ViewType.Elevation,
    DB.ViewType.Section,
    DB.ViewType.FloorPlan,
    DB.ViewType.CeilingPlan,
    DB.ViewType.EngineeringPlan,
)

REASON_COLORS = {
    "element_hidden": (229, 57, 53),
    "temporary_hidden": (229, 57, 53),
    "category_hidden": (255, 152, 0),
    "subcategory_hidden": (255, 152, 0),
    "view_filter": (233, 30, 99),
    "workset_hidden": (156, 39, 176),
    "workset_closed": (156, 39, 176),
    "workset_default_hidden": (156, 39, 176),
    "phase_filter": (0, 150, 136),
    "design_option": (0, 150, 136),
    "detail_level": (121, 85, 72),
    "section_box": (33, 150, 243),
    "crop_box": (33, 150, 243),
    "behind_cut_plane": (33, 150, 243),
    "far_clip": (33, 150, 243),
    "above_cut_plane": (76, 175, 80),
    "viewrange_above": (76, 175, 80),
    "viewrange_below": (76, 175, 80),
    "view_specific": (96, 125, 139),
    "unknown": (158, 158, 158),
}

_REASON_PRIORITY = (
    "element_hidden",
    "temporary_hidden",
    "category_hidden",
    "subcategory_hidden",
    "view_filter",
    "workset_hidden",
    "workset_closed",
    "workset_default_hidden",
    "phase_filter",
    "design_option",
    "detail_level",
    "section_box",
    "crop_box",
    "behind_cut_plane",
    "far_clip",
    "above_cut_plane",
    "viewrange_above",
    "viewrange_below",
    "view_specific",
    "unknown",
)

_OVERLAY_ALPHA = 120
_FAR_FT = 2000.0
_CLIP_MARGIN_FACTOR = 1.0
_MIN_SIZE_FRACTION = 0.004
_TIME_BUDGET_S = 3.0
_MAX_EVALUATED = 2500
_MAX_SOLID_ELEMENTS = 150
_MAX_TRIANGLES = 80000
_FOLLOW_DEBOUNCE_S = 0.4


def color_hex(code):
    """Return the overlay color of a reason code as ``#rrggbb``."""
    red, green, blue = REASON_COLORS.get(code, REASON_COLORS["unknown"])
    return "#{:02x}{:02x}{:02x}".format(red, green, blue)


def _overlay_color(code):
    red, green, blue = REASON_COLORS.get(code, REASON_COLORS["unknown"])
    return DB.ColorWithTransparency(red, green, blue, _OVERLAY_ALPHA)


def zoom_corners(uidoc, view):
    """Return the two corners of the zoomed screen area of ``view``, or None.

    None when the view is not open in the UI.
    """
    for ui_view in uidoc.GetOpenUIViews():
        if ui_view.ViewId == view.Id:
            corners = ui_view.GetZoomCorners()
            return corners[0], corners[1]
    return None


def _outline_of(points):
    low = DB.XYZ(
        min(p.X for p in points), min(p.Y for p in points), min(p.Z for p in points)
    )
    high = DB.XYZ(
        max(p.X for p in points), max(p.Y for p in points), max(p.Z for p in points)
    )
    return DB.Outline(low, high)


def _box_outline(box, margin_factor=0.0):
    size = box.Max - box.Min
    margin = max(size.X, size.Y, size.Z) * margin_factor
    points = [
        box.Transform.OfPoint(
            DB.XYZ(
                x + (margin if x == box.Max.X else -margin),
                y + (margin if y == box.Max.Y else -margin),
                z + (margin if z == box.Max.Z else -margin),
            )
        )
        for x in (box.Min.X, box.Max.X)
        for y in (box.Min.Y, box.Max.Y)
        for z in (box.Min.Z, box.Max.Z)
    ]
    return _outline_of(points)


def search_outline(view, corners):
    """Return the world-space outline to search for candidates, or None.

    All four corners of the screen rectangle are rebuilt from the view axes,
    so a rotated plan is covered, and extruded both ways along the view
    direction, so elements hidden by cut plane, view range or far clip are
    still found. A 3D view has no usable screen rectangle: its section box or
    crop box, grown by its own largest size on every side, limits the search
    so that elements clipped away by the box are still candidates; without a
    box the whole model is searched.
    """
    if view.ViewType == DB.ViewType.ThreeD:
        if view.IsSectionBoxActive:
            return _box_outline(view.GetSectionBox(), _CLIP_MARGIN_FACTOR)
        if view.CropBoxActive:
            return _box_outline(view.CropBox, _CLIP_MARGIN_FACTOR)
        return None
    if corners is None:
        return _box_outline(view.CropBox) if view.CropBoxActive else None
    first, second = corners
    span = second - first
    across = view.RightDirection * span.DotProduct(view.RightDirection)
    up = view.UpDirection * span.DotProduct(view.UpDirection)
    direction = view.ViewDirection * _FAR_FT
    points = []
    for corner in (first, first + across, first + up, second):
        points.extend([corner + direction, corner - direction])
    return _outline_of(points)


def _primary_reason(element, view, visible_ids):
    findings = [
        finding
        for finding in diagnose(element, view, visible_ids)
        if not finding.informational
    ]
    if not findings:
        return None
    confirmed = [finding for finding in findings if not finding.speculative]
    codes = [finding.code for finding in (confirmed or findings)]
    for code in _REASON_PRIORITY:
        if code in codes:
            return code
    return codes[0]


def _is_candidate(element, view):
    try:
        category = element.Category
        if category is None or category.CategoryType == DB.CategoryType.Internal:
            return None
        owner_id = element.OwnerViewId
        if owner_id != DB.ElementId.InvalidElementId and owner_id != view.Id:
            return None
        box = element.get_BoundingBox(None)
        if box is None:
            return None
        return (box.Max - box.Min).GetLength(), box
    except Exception as ex:
        logger.debug("Skipping candidate: %s", ex)
        return None


def _candidates(view, outline, min_size, visible_ids):
    """Return ``(entries, too_small)``, hidden elements first, then biggest first.

    Elements the view collector reports are kept, after the others: it still
    lists elements that have no geometry at the view's detail level or sit
    outside the crop, which only ``diagnose`` can tell.
    """
    collector = DB.FilteredElementCollector(
        view.Document
    ).WhereElementIsNotElementType()
    if outline is not None:
        collector = collector.WherePasses(DB.BoundingBoxIntersectsFilter(outline))
    found = []
    too_small = 0
    for element in collector:
        measured = _is_candidate(element, view)
        if measured is None:
            continue
        if measured[0] < min_size:
            too_small += 1
            continue
        found.append(
            (
                measured[0],
                element,
                measured[1],
                id_value(element.Id) in visible_ids,
            )
        )
    found.sort(key=lambda entry: (entry[3], -entry[0]))
    return found, too_small


def _triangle_count(meshes):
    return sum(len(mesh.triangles) for mesh in meshes)


def build_overlay(uidoc, view):
    """Diagnose the hidden elements of ``view``'s screen area and mesh them.

    Returns:
        (tuple[dict, dict]): ``(summary, meshes_by_code)``. The summary holds
        ``counts`` and ``ids`` per reason code, ``drawn``, ``notEvaluated``
        and ``tooSmall``; meshes are ready for ``dc3dserver.Server``.
    """
    corners = zoom_corners(uidoc, view)
    min_size = (
        (corners[1] - corners[0]).GetLength() * _MIN_SIZE_FRACTION if corners else 0.0
    )
    visible_ids = collect_visible_ids(view)
    candidates, too_small = _candidates(
        view, search_outline(view, corners), min_size, visible_ids
    )

    started = time.time()
    by_code = {}
    evaluated = 0
    for size, element, box, _ in candidates:
        if evaluated >= _MAX_EVALUATED or time.time() - started > _TIME_BUDGET_S:
            break
        evaluated += 1
        try:
            code = _primary_reason(element, view, visible_ids)
        except Exception as ex:
            logger.debug("Diagnosis failed: %s", ex)
            continue
        if code:
            by_code.setdefault(code, []).append((size, element, box))
    not_evaluated = len(candidates) - evaluated

    ranked = sorted(
        (
            (size, code, element, box)
            for code, entries in by_code.items()
            for size, element, box in entries
        ),
        key=lambda entry: entry[0],
        reverse=True,
    )
    meshes_by_code = {}
    triangles = 0
    for rank, (size, code, element, box) in enumerate(ranked):
        color = _overlay_color(code)
        meshes = []
        if rank < _MAX_SOLID_ELEMENTS:
            meshes = element_meshes(element, color, DB.ViewDetailLevel.Coarse)
        if not meshes or triangles + _triangle_count(meshes) > _MAX_TRIANGLES:
            mesh = dc3dserver.Mesh.from_boundingbox(box, color, black_edges=False)
            meshes = [mesh] if mesh is not None else []
        triangles += _triangle_count(meshes)
        meshes_by_code.setdefault(code, []).extend(meshes)

    summary = {
        "viewId": id_value(view.Id),
        "active": True,
        "counts": dict((code, len(entries)) for code, entries in by_code.items()),
        "ids": dict(
            (code, [id_value(element.Id) for _, element, _ in entries])
            for code, entries in by_code.items()
        ),
        "drawn": len(ranked),
        "notEvaluated": not_evaluated,
        "tooSmall": too_small,
        "seconds": round(time.time() - started, 2),
    }
    return summary, meshes_by_code


class _ViewServer(dc3dserver.Server):
    """DirectContext3D server that draws in a single view only."""

    def __init__(self, view_id, uidoc, name, description):
        self.view_id = view_id
        super(_ViewServer, self).__init__(
            uidoc=uidoc, name=name, description=description
        )

    def CanExecute(self, view):
        return view.Id == self.view_id and super(_ViewServer, self).CanExecute(view)


def _corner_key(corners):
    if corners is None:
        return None
    return tuple(
        round(value, 1)
        for corner in corners
        for value in (corner.X, corner.Y, corner.Z)
    )


class RevealPreview(object):
    """The reveal overlay of one view of a report.

    At most one view is revealed at a time. ``show`` builds the overlay once
    the view is the active one; ``refresh`` rebuilds it from the current
    screen area; ``follow`` rebuilds it after the user stops panning or
    zooming.

    Important:
        ``show``, ``refresh``, ``follow``, ``set_code_visible`` and ``close``
        touch Revit's external service registry, events and the UI, so they
        must run in Revit API context.
    """

    def __init__(self, doc):
        self.doc = doc
        self.view_id = None
        self._server = None
        self._meshes_by_code = {}
        self._ids_by_code = {}
        self._hidden_codes = set()
        self._on_built = None
        self._following = False
        self._idling_handler = self._on_idling
        self._seen_key = None
        self._built_key = None
        self._changed_at = 0.0
        self._pending = []

    def show(self, uidoc, view, on_built):
        """Reveal ``view``, opening it first when it is not the active view.

        Args:
            uidoc (UI.UIDocument): the document the report belongs to.
            view (DB.View): the view to reveal; must be of a supported type.
            on_built (callable): called with the summary dict each time an
                overlay was built, including the first one.
        """
        self._cancel_pending()
        self._on_built = on_built
        if self.view_id != view.Id:
            self._hidden_codes = set()
        self.view_id = view.Id
        if uidoc.ActiveView.Id == view.Id:
            self._build(uidoc, view)
            return
        self._build_after_activation(view)
        uidoc.RequestViewChange(view)

    def refresh(self, uidoc):
        """Rebuild the overlay from the view's current screen area."""
        view = self._target_view(uidoc)
        if view is not None:
            self._build(uidoc, view)

    def follow(self, on):
        """Rebuild automatically after the screen area stops changing."""
        uiapp = HOST_APP.uiapp
        if on and not self._following:
            uiapp.Idling += self._idling_handler
            self._following = True
        elif not on and self._following:
            uiapp.Idling -= self._idling_handler
            self._following = False

    def set_code_visible(self, uidoc, code, visible):
        """Show or hide one reason's meshes without rebuilding."""
        if visible:
            self._hidden_codes.discard(code)
        else:
            self._hidden_codes.add(code)
        self._apply_meshes(uidoc)

    def ids_for(self, code):
        """Return the element id values drawn for a reason."""
        return list(self._ids_by_code.get(code, []))

    def close(self):
        """Remove the overlay, stop following and unregister the server."""
        self._cancel_pending()
        self.follow(False)
        self.view_id = None
        self._meshes_by_code = {}
        self._ids_by_code = {}
        self._hidden_codes = set()
        if self._server is not None:
            try:
                self._server.meshes = []
                self._server.remove_server()
            except Exception as ex:
                logger.debug("Cannot remove the reveal server: %s", ex)
            self._server = None
        try:
            uidoc = HOST_APP.uiapp.ActiveUIDocument
            if uidoc is not None:
                uidoc.RefreshActiveView()
        except Exception as ex:
            logger.debug("Cannot refresh the view: %s", ex)

    def _target_view(self, uidoc):
        if self.view_id is None:
            return None
        view = self.doc.GetElement(self.view_id)
        if view is None:
            return None
        if uidoc.ActiveView.Id != view.Id:
            self.show(uidoc, view, self._on_built)
            return None
        return view

    def _build(self, uidoc, view):
        summary, meshes_by_code = build_overlay(uidoc, view)
        self._meshes_by_code = meshes_by_code
        self._ids_by_code = summary.pop("ids")
        summary["follow"] = self._following
        self._built_key = _corner_key(zoom_corners(uidoc, view))
        self._seen_key = self._built_key
        if self._server is None:
            self._server = _ViewServer(
                view.Id,
                uidoc,
                "pyRevit Diagnose Invisibility reveal",
                "Hidden elements of a view, colored by reason",
            )
        self._server.view_id = view.Id
        self._apply_meshes(uidoc)
        if self._on_built is not None:
            self._on_built(summary)

    def _apply_meshes(self, uidoc):
        if self._server is None:
            return
        meshes = []
        for code, code_meshes in self._meshes_by_code.items():
            if code not in self._hidden_codes:
                meshes.extend(code_meshes)
        self._server.meshes = meshes
        uidoc.RefreshActiveView()

    def _on_idling(self, sender, args):
        uidoc = HOST_APP.uiapp.ActiveUIDocument
        if not self._is_target(uidoc):
            return
        key = _corner_key(zoom_corners(uidoc, uidoc.ActiveView))
        now = time.time()
        if key != self._seen_key:
            self._seen_key = key
            self._changed_at = now
        elif key != self._built_key and now - self._changed_at >= _FOLLOW_DEBOUNCE_S:
            self._build(uidoc, uidoc.ActiveView)

    def _is_target(self, uidoc):
        return (
            uidoc is not None
            and self.view_id is not None
            and uidoc.Document.Equals(self.doc)
            and uidoc.ActiveView.Id == self.view_id
        )

    def _build_after_activation(self, view):
        """Build once ``view`` is active and settled.

        Revit restores a view's saved zoom after ``ViewActivated``, so the
        first ``Idling`` after it is used.
        """
        uiapp = HOST_APP.uiapp
        view_id = view.Id

        def on_idling(sender, args):
            self._cancel_pending()
            uidoc = uiapp.ActiveUIDocument
            if self._is_target(uidoc) and uidoc.ActiveView.Id == view_id:
                self._build(uidoc, uidoc.ActiveView)

        def on_view_activated(sender, args):
            if args.CurrentActiveView is None or args.CurrentActiveView.Id != view_id:
                return
            self._cancel_pending()
            uiapp.Idling += on_idling
            self._pending.append(("Idling", on_idling))

        uiapp.ViewActivated += on_view_activated
        self._pending.append(("ViewActivated", on_view_activated))

    def _cancel_pending(self):
        uiapp = HOST_APP.uiapp
        pending, self._pending = self._pending, []
        for event_name, handler in pending:
            try:
                if event_name == "Idling":
                    uiapp.Idling -= handler
                else:
                    uiapp.ViewActivated -= handler
            except Exception as ex:
                logger.debug("Cannot detach %s handler: %s", event_name, ex)
