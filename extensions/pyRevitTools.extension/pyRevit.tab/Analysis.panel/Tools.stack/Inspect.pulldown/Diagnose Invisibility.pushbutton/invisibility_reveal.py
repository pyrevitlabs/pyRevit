# -*- coding: utf-8 -*-
"""Reveal-hidden overlay: draw what a view hides, colored by the reason.

Revit's own Reveal Hidden Elements shows only what the Hide command hid. This
overlay runs the same checks as the report on every element in the screen
area of one view and draws the hidden ones through a DirectContext3D server
(``pyrevit.revit.dc3dserver``), one color per reason. It never changes the
model.

Cost is bounded on purpose: candidates come from a bounding-box filter on the
zoomed screen area, tiny elements and categories a view can never draw are
skipped, explicitly hidden elements are diagnosed first, a time budget stops the
diagnosis, and only the largest elements are drawn as solids (the rest as
boxes). The summary reports what was left out.

Warning:
    The server is registered with Revit's DirectContext3D service and the
    optional follow mode hooks ``Idling``. Both stay until
    ``RevealPreview.close`` runs, in Revit API context. The report closes the
    preview when its output window closes.
"""

import time
from collections import namedtuple

from pyrevit import DB, HOST_APP
from pyrevit.compat import get_elementid_from_value_func
from pyrevit.coreutils.logger import get_logger
from pyrevit.revit import dc3dserver, query

from invisibility_checks import (
    NOT_IN_3D_CATEGORIES,
    collect_visible_ids,
    diagnose,
    id_value,
)
from invisibility_ghost import element_meshes

logger = get_logger(__name__)

_element_id = get_elementid_from_value_func()

_NEVER_DRAWN_CATEGORY_NAMES = (
    "OST_Sheets",
    "OST_AreaSchemeLines",
    "OST_CLines",
    "OST_SketchLines",
)

SUPPORTED_VIEW_TYPES = (
    DB.ViewType.ThreeD,
    DB.ViewType.Elevation,
    DB.ViewType.Section,
    DB.ViewType.FloorPlan,
    DB.ViewType.CeilingPlan,
    DB.ViewType.EngineeringPlan,
)

REASON_COLORS = {
    "view_type": (205, 220, 57),
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
    "view_type",
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
_OPAQUE = 0
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


def _overlay_color(code, transparency=_OVERLAY_ALPHA):
    red, green, blue = REASON_COLORS.get(code, REASON_COLORS["unknown"])
    return DB.ColorWithTransparency(red, green, blue, transparency)


def _never_drawn_category_ids(view):
    names = list(_NEVER_DRAWN_CATEGORY_NAMES)
    categories = [getattr(DB.BuiltInCategory, name, None) for name in names]
    if view.ViewType == DB.ViewType.ThreeD:
        categories.extend(NOT_IN_3D_CATEGORIES)
    return set(
        id_value(DB.ElementId(category))
        for category in categories
        if category is not None
    )


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


def _is_candidate(element, view, never_drawn):
    try:
        category = element.Category
        if (
            category is None
            or category.CategoryType == DB.CategoryType.Internal
            or id_value(category.Id) in never_drawn
        ):
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


def _candidates(view, outline, min_size, visible_ids, matches=None):
    """Return ``(entries, too_small)``, in the order the time budget spends them.

    Elements hidden with Hide/Isolate come first, then the other elements
    the collector does not report, each biggest first. Elements the view
    collector reports are kept, after those: it still lists elements that
    have no geometry at the view's detail level or sit outside the crop,
    which only ``diagnose`` can tell. Categories the view can never draw
    (sheets, reference planes, sketches, rooms in 3D) are not candidates;
    neither are elements ``matches`` rejects.
    """
    collector = DB.FilteredElementCollector(
        view.Document
    ).WhereElementIsNotElementType()
    if outline is not None:
        collector = collector.WherePasses(DB.BoundingBoxIntersectsFilter(outline))
    never_drawn = _never_drawn_category_ids(view)
    found = []
    too_small = 0
    for element in collector:
        measured = _is_candidate(element, view, never_drawn)
        if measured is None or (matches is not None and not matches(element)):
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
                _is_explicitly_hidden(element, view),
            )
        )
    found.sort(key=lambda entry: (entry[3], not entry[4], -entry[0]))
    return found, too_small


def _is_explicitly_hidden(element, view):
    try:
        return element.IsHidden(view)
    except Exception as ex:
        logger.debug("Cannot read the hidden state: %s", ex)
        return False


Hit = namedtuple("Hit", ("id", "code", "size", "box"))


def _type_name(element, cache):
    try:
        type_id = element.GetTypeId()
        if type_id == DB.ElementId.InvalidElementId:
            return query.get_name(element)
        key = id_value(type_id)
        if key not in cache:
            type_element = element.Document.GetElement(type_id)
            family = getattr(type_element, "FamilyName", "")
            name = query.get_name(type_element)
            cache[key] = "{} : {}".format(family, name) if family else name
        return cache[key]
    except Exception as ex:
        logger.debug("Cannot read the type name: %s", ex)
        return ""


def _level_name(element, cache):
    try:
        level_id = element.LevelId
        if level_id == DB.ElementId.InvalidElementId:
            return ""
        key = id_value(level_id)
        if key not in cache:
            level = element.Document.GetElement(level_id)
            cache[key] = query.get_name(level) if level is not None else ""
        return cache[key]
    except Exception as ex:
        logger.debug("Cannot read the level: %s", ex)
        return ""


def _mark(element):
    try:
        return query.get_mark(element) or ""
    except Exception as ex:
        logger.debug("Cannot read the mark: %s", ex)
        return ""


def _scope_matcher(scope, names):
    """Return a predicate for the elements the page's filter keeps.

    ``scope`` holds ``query``, ``categories`` and ``level``. Every query term
    must occur in the category, type, level, mark or id; reasons are unknown
    before the diagnosis, so they cannot be searched here.
    """
    terms = [term for term in (scope.get("query") or "").lower().split() if term]
    categories = set(scope.get("categories") or [])
    level = scope.get("level") or ""

    def matches(element):
        category = element.Category
        category_name = category.Name if category else ""
        if categories and category_name not in categories:
            return False
        level_name = _level_name(element, names["levels"])
        if level and level_name != level:
            return False
        if not terms:
            return True
        haystack = " ".join(
            (
                category_name,
                _type_name(element, names["types"]),
                level_name,
                _mark(element),
                str(id_value(element.Id)),
            )
        ).lower()
        return all(term in haystack for term in terms)

    return matches


def _row(element, code, size, names):
    category = element.Category
    return {
        "id": id_value(element.Id),
        "code": code,
        "category": category.Name if category else "",
        "name": _type_name(element, names["types"]),
        "level": _level_name(element, names["levels"]),
        "mark": _mark(element),
        "size": round(size, 2),
    }


def _evaluate(element, view, visible_ids, size, box, names):
    try:
        code = _primary_reason(element, view, visible_ids)
    except Exception as ex:
        logger.debug("Diagnosis failed: %s", ex)
        return None
    if not code:
        return None
    return Hit(id_value(element.Id), code, size, box), _row(element, code, size, names)


def _measure(element):
    box = element.get_BoundingBox(None)
    return ((box.Max - box.Min).GetLength() if box is not None else 0.0), box


def _triangle_count(meshes):
    return sum(len(mesh.triangles) for mesh in meshes)


def build_overlay(uidoc, view, pinned_ids=(), scope=None):
    """Diagnose the hidden elements of ``view``'s screen area.

    Args:
        uidoc (UI.UIDocument): the document of ``view``.
        view (DB.View): the active view.
        pinned_ids (Iterable[int]): element id values to diagnose whatever
            their size, screen position or the time budget, such as elements
            the user added from the Revit selection.
        scope (dict | None): the page's filter (``query``, ``categories``,
            ``level``). Only elements it keeps are candidates, so the time
            budget is spent on them instead of the biggest elements.

    Returns:
        (tuple[list[Hit], dict, dict]): the hidden elements found, a row per
        element keyed by id value (code, category, type name, level, mark,
        size), and the stats ``notEvaluated``, ``tooSmall``, ``seconds`` and
        ``scoped``.
    """
    corners = zoom_corners(uidoc, view)
    min_size = (
        (corners[1] - corners[0]).GetLength() * _MIN_SIZE_FRACTION if corners else 0.0
    )
    visible_ids = collect_visible_ids(view)
    names = {"types": {}, "levels": {}}
    candidates, too_small = _candidates(
        view,
        search_outline(view, corners),
        min_size,
        visible_ids,
        _scope_matcher(scope, names) if scope else None,
    )

    started = time.time()
    hits = []
    rows = {}
    evaluated = 0
    for size, element, box, _, _ in candidates:
        if evaluated >= _MAX_EVALUATED or time.time() - started > _TIME_BUDGET_S:
            break
        evaluated += 1
        found = _evaluate(element, view, visible_ids, size, box, names)
        if found is not None:
            hits.append(found[0])
            rows[found[0].id] = found[1]
    not_evaluated = len(candidates) - evaluated
    for value in pinned_ids:
        element = view.Document.GetElement(_element_id(value))
        if value in rows or element is None:
            continue
        size, box = _measure(element)
        found = _evaluate(element, view, visible_ids, size, box, names)
        if found is not None:
            hits.append(found[0])
            rows[found[0].id] = found[1]

    stats = {
        "notEvaluated": not_evaluated,
        "tooSmall": too_small,
        "seconds": round(time.time() - started, 2),
        "scoped": bool(scope),
    }
    return hits, rows, stats


def mesh_hits(doc, hits, only_ids=None):
    """Mesh ``hits`` for ``dc3dserver.Server``, biggest first.

    The ``_MAX_SOLID_ELEMENTS`` biggest are drawn as solids, the rest, and any
    that would pass the triangle cap, as boxes; so meshing a filtered subset
    spends the whole budget on it.

    Args:
        doc (DB.Document): resolves the hit ids.
        hits (list[Hit]): result of ``build_overlay``.
        only_ids (set[int] | None): mesh only these id values.

    Returns:
        (dict): meshes per element id value.
    """
    chosen = sorted(
        (hit for hit in hits if only_ids is None or hit.id in only_ids),
        key=lambda hit: hit.size,
        reverse=True,
    )
    meshes_by_id = {}
    triangles = 0
    for rank, hit in enumerate(chosen):
        element = doc.GetElement(_element_id(hit.id))
        if element is None:
            continue
        color = _overlay_color(hit.code)
        edge_color = _overlay_color(hit.code, _OPAQUE)
        meshes = []
        if rank < _MAX_SOLID_ELEMENTS:
            meshes = element_meshes(
                element, color, DB.ViewDetailLevel.Coarse, edge_color=edge_color
            )
        if not meshes or triangles + _triangle_count(meshes) > _MAX_TRIANGLES:
            mesh = (
                dc3dserver.Mesh.from_boundingbox(hit.box, color, edge_color=edge_color)
                if hit.box is not None
                else None
            )
            meshes = [mesh] if mesh is not None else []
        triangles += _triangle_count(meshes)
        meshes_by_id[hit.id] = meshes
    return meshes_by_id


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

    Each hidden element has a row (reason, category, type, level, mark) the
    page lists and filters. ``set_focus`` narrows the drawing to chosen
    elements and meshes just those, so a filtered handful gets solids even
    when hundreds are hidden; ``add_elements`` diagnoses chosen elements
    whatever their size and keeps them through rebuilds.

    Important:
        ``show``, ``refresh``, ``follow``, ``set_code_visible``,
        ``set_focus``, ``add_elements`` and ``close`` touch Revit's external
        service registry, events and the UI, so they must run in Revit API
        context.
    """

    def __init__(self, doc):
        self.doc = doc
        self.view_id = None
        self._server = None
        self._hits = []
        self._rows = {}
        self._stats = {}
        self._base_meshes = {}
        self._focus_ids = None
        self._focus_meshes = {}
        self._pinned_ids = set()
        self._scope = None
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
            self._pinned_ids = set()
            self._focus_ids = None
            self._scope = None
        self.view_id = view.Id
        if uidoc.ActiveView.Id == view.Id:
            self._build(uidoc, view)
            return
        self._build_after_activation(view)
        uidoc.RequestViewChange(view)

    def refresh(self, uidoc, scope=None):
        """Rebuild the overlay from the view's current screen area.

        Args:
            uidoc (UI.UIDocument): the document the report belongs to.
            scope (dict | None): evaluate only the elements this filter keeps
                (see ``build_overlay``). It stays in force for rebuilds by
                ``follow`` until the next ``refresh`` without one.
        """
        self._scope = scope
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

    def set_focus(self, uidoc, ids):
        """Draw only the elements with these id values; ``None`` draws all.

        Meshes the chosen elements afresh, with the full solid budget. The
        focus survives rebuilds until it is cleared.
        """
        self._focus_ids = None if ids is None else set(int(value) for value in ids)
        self._mesh_focus()
        self._apply_meshes(uidoc)

    def add_elements(self, uidoc, elements):
        """Diagnose ``elements`` in the revealed view and draw the hidden ones.

        They are drawn whatever their size, and pinned: later rebuilds
        diagnose them again, even when they sit outside the screen area.

        Returns:
            (tuple[list[int], int]): the id values added to the overlay and
            the number of elements the view already shows, which need no
            reveal.
        """
        view = self._target_view(uidoc)
        if view is None:
            return [], 0
        visible_ids = collect_visible_ids(view)
        names = {"types": {}, "levels": {}}
        added = []
        for element in elements:
            if element is None or element.Category is None:
                continue
            size, box = _measure(element)
            found = _evaluate(element, view, visible_ids, size, box, names)
            if found is None:
                continue
            self._pinned_ids.add(found[0].id)
            self._hits = [hit for hit in self._hits if hit.id != found[0].id]
            self._hits.append(found[0])
            self._rows[found[0].id] = found[1]
            added.append(found[0])
        ids = set(hit.id for hit in added)
        self._base_meshes.update(mesh_hits(self.doc, self._hits, ids))
        self._mesh_focus()
        self._apply_meshes(uidoc)
        if self._on_built is not None:
            self._on_built(self.summary())
        return [hit.id for hit in added], len(elements) - len(added)

    def summary(self):
        """Return what the page lists: counts per reason, rows and stats."""
        counts = {}
        for row in self._rows.values():
            counts[row["code"]] = counts.get(row["code"], 0) + 1
        summary = {
            "viewId": id_value(self.view_id),
            "active": True,
            "counts": counts,
            "drawn": len(self._rows),
            "rows": sorted(
                self._rows.values(), key=lambda row: row["size"], reverse=True
            ),
            "follow": self._following,
        }
        summary.update(self._stats)
        return summary

    def ids_for(self, code):
        """Return the element id values drawn for a reason."""
        return [value for value, row in self._rows.items() if row["code"] == code]

    def close(self):
        """Remove the overlay, stop following and unregister the server."""
        self._cancel_pending()
        self.follow(False)
        self.view_id = None
        self._hits = []
        self._rows = {}
        self._stats = {}
        self._base_meshes = {}
        self._focus_ids = None
        self._focus_meshes = {}
        self._pinned_ids = set()
        self._scope = None
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
        self._hits, self._rows, self._stats = build_overlay(
            uidoc, view, self._pinned_ids, self._scope
        )
        self._base_meshes = mesh_hits(self.doc, self._hits)
        self._mesh_focus()
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
            self._on_built(self.summary())

    def _mesh_focus(self):
        if self._focus_ids is None:
            self._focus_meshes = {}
        else:
            self._focus_meshes = mesh_hits(self.doc, self._hits, self._focus_ids)

    def _apply_meshes(self, uidoc):
        if self._server is None:
            return
        source = self._base_meshes if self._focus_ids is None else self._focus_meshes
        meshes = []
        for value, item_meshes in source.items():
            if self._rows[value]["code"] not in self._hidden_codes:
                meshes.extend(item_meshes)
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
