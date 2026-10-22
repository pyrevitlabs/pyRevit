# -*- coding: utf-8 -*-
"""Visibility checks behind the Diagnose Invisibility tool.

Each check inspects one Revit mechanism that can hide an element in a view and
returns ``Finding`` records. A finding may carry a fix descriptor: a plain,
JSON-serializable dict naming an action implemented in ``invisibility_fixes``.
Descriptors hold ids only, never live API objects, so they survive a round
trip through the report page and are re-validated before anything changes.
"""

import os

from pyrevit import DB
from pyrevit.compat import get_elementid_value_func
from pyrevit.coreutils import applocales
from pyrevit.revit import query

get_elementid_value = get_elementid_value_func()

RESX_BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources.xaml")

_TOLERANCE = 1e-6

LEGACY_SHORT_CODES = {
    "workset_hidden": "Workset hidden",
    "workset_closed": "Workset closed",
    "workset_default_hidden": "Workset default hidden",
    "phase_filter": "Phase Filter",
    "design_option": "Design Option",
    "category_hidden": "Category",
    "subcategory_hidden": "Subcategory",
    "element_hidden": "Hidden",
    "temporary_hidden": "Temporary hide",
    "view_filter": "Viewfilter",
    "section_box": "SectionBox",
    "crop_box": "CropBox",
    "behind_cut_plane": "Cut plane",
    "far_clip": "Far clip",
    "viewrange_above": "Viewrange",
    "viewrange_below": "Viewrange",
    "above_cut_plane": "Above cut plane",
    "view_template": "Viewtemplate",
    "view_specific": "View-specific",
    "view_discipline": "Discipline",
    "unknown": "Hidden unknown",
}


def t(key, default=None):
    """Look up a localized UI string, falling back to en_us, then ``default``.

    Resolves against the bundle's ``resources.ResourceDictionary.<locale>.xaml``
    files through a module-relative path, so it also works from deferred
    callbacks that run after the command returned.
    """
    result = applocales.get_locale_string_from_xaml(RESX_BASE, key)
    if result == key and default is not None:
        return default
    return result


class Finding(object):
    """One reason an element is not visible in a view.

    Attributes:
        code (str): stable identifier, used for grouping and filtering.
        message (str): localized explanation shown to the user.
        informational (bool): context that may matter but is not a confirmed
            cause (e.g. an applied view template).
        fix (dict | None): fix descriptor for ``invisibility_fixes``.
        speculative (bool): a possible cause that could not be confirmed.
            Its fix stays available per element but is never applied in
            bulk, since it may change settings that are hidden on purpose.
    """

    __slots__ = ("code", "message", "informational", "fix", "speculative")

    def __init__(self, code, message, informational=False, fix=None, speculative=False):
        self.code = code
        self.message = message
        self.informational = informational
        self.fix = fix
        self.speculative = speculative

    def __repr__(self):
        return "<Finding {}>".format(self.code)


class _CheckContext(object):
    """Per (element, view) state shared by the checks."""

    def __init__(self, element, view):
        self.element = element
        self.view = view
        self.doc = element.Document
        self.element_id = id_value(element.Id)
        self._world_bbox = None
        self._world_bbox_read = False

    @property
    def world_bbox(self):
        """Model-space bounding box, falling back to the view-specific one."""
        if not self._world_bbox_read:
            self._world_bbox_read = True
            try:
                self._world_bbox = self.element.get_BoundingBox(None)
                if self._world_bbox is None:
                    self._world_bbox = self.element.get_BoundingBox(self.view)
            except Exception:
                self._world_bbox = None
        return self._world_bbox

    @property
    def is_view_specific(self):
        try:
            owner_id = self.element.OwnerViewId
            return owner_id is not None and owner_id != DB.ElementId.InvalidElementId
        except Exception:
            return False


def id_value(element_id):
    """Return an element id as a Python int (JSON-safe on every Revit version)."""
    return int(get_elementid_value(element_id))


def _is_valid_id(element_id):
    return element_id is not None and element_id != DB.ElementId.InvalidElementId


def collect_visible_ids(view):
    """Return the id values the view's element collector reports as visible.

    This is the expensive part of a diagnosis; collect it once per view and
    pass it to ``diagnose`` for every element.
    """
    return set(id_value(e.Id) for e in query.get_all_elements_in_view(view))


def local_extents(transform, bbox):
    """Return the (min, max) XYZ of ``bbox`` expressed in ``transform``'s space.

    Args:
        transform (DB.Transform): local-to-world transform (e.g. a crop box's).
        bbox (DB.BoundingBoxXYZ): world-space bounding box.
    """
    inverse = transform.Inverse
    points = [
        inverse.OfPoint(DB.XYZ(x, y, z))
        for x in (bbox.Min.X, bbox.Max.X)
        for y in (bbox.Min.Y, bbox.Max.Y)
        for z in (bbox.Min.Z, bbox.Max.Z)
    ]
    low = DB.XYZ(
        min(p.X for p in points), min(p.Y for p in points), min(p.Z for p in points)
    )
    high = DB.XYZ(
        max(p.X for p in points), max(p.Y for p in points), max(p.Z for p in points)
    )
    return low, high


def _get_workset_id(element):
    if not element.Document.IsWorkshared:
        return None
    try:
        ws_param = element.get_Parameter(DB.BuiltInParameter.ELEM_PARTITION_PARAM)
        if ws_param:
            return DB.WorksetId(ws_param.AsInteger())
    except Exception:
        pass
    return None


def _get_level_elevation(doc, level_id):
    if not _is_valid_id(level_id):
        return None
    try:
        level = doc.GetElement(level_id)
        if level and hasattr(level, "Elevation"):
            return level.Elevation
    except Exception:
        pass
    return None


def resolve_view_range_elevation(doc, view_range, plane):
    """Resolve a PlanViewPlane to an absolute elevation (feet).

    Returns None when the plane is set to "Unlimited" or cannot be resolved.
    """
    try:
        base = _get_level_elevation(doc, view_range.GetLevelId(plane))
        if base is not None:
            return base + view_range.GetOffset(plane)
    except Exception:
        pass
    return None


def get_view_range_bounds(doc, view):
    """Return (lower_elev, upper_elev) absolute elevations of a plan view range.

    Either value may be None if the plane is Unlimited or unresolvable.

    For floor, area and engineering plans the lower bound is the lower of the
    bottom clip and view depth planes: elements between the two still render
    (as "beyond"), so only elements below both are out of range. The upper
    bound is the top clip plane.

    For ceiling plans (RCP) the relationship flips per Autodesk's documented
    view range behavior: the cut plane coincides with the bottom clip plane,
    and the view depth plane extends further up than the top clip plane. So
    the upper bound is the higher of top and view depth, and the lower bound
    is the bottom/cut plane.
    """
    try:
        view_range = view.GetViewRange()
        top = resolve_view_range_elevation(
            doc, view_range, DB.PlanViewPlane.TopClipPlane
        )
        bottom = resolve_view_range_elevation(
            doc, view_range, DB.PlanViewPlane.BottomClipPlane
        )
        depth = resolve_view_range_elevation(
            doc, view_range, DB.PlanViewPlane.ViewDepthPlane
        )
        if view.ViewType == DB.ViewType.CeilingPlan:
            upper_candidates = [v for v in (top, depth) if v is not None]
            return bottom, (max(upper_candidates) if upper_candidates else None)
        lower_candidates = [v for v in (bottom, depth) if v is not None]
        return (min(lower_candidates) if lower_candidates else None), top
    except Exception:
        return None, None


def _check_workset(ctx):
    """Workset hidden in the view, closed, or hidden by default visibility.

    A workset can be open and still hidden by the model's default workset
    visibility setting; ``IsOpen`` alone does not tell us that.
    """
    findings = []
    if not ctx.doc.IsWorkshared:
        return findings
    ws_id = _get_workset_id(ctx.element)
    if not ws_id:
        return findings
    try:
        workset = ctx.doc.GetWorksetTable().GetWorkset(ws_id)
        ws_name = workset.Name if workset else "?"
        visibility = ctx.view.GetWorksetVisibility(ws_id)
        fix = {"action": "show_workset", "workset_id": int(ws_id.IntegerValue)}
        if visibility == DB.WorksetVisibility.Hidden:
            findings.append(
                Finding(
                    "workset_hidden",
                    t(
                        "reason_workset_hidden",
                        "Workset '{}' is explicitly hidden in this view",
                    ).format(ws_name),
                    fix=fix,
                )
            )
        elif visibility == DB.WorksetVisibility.UseGlobalSetting:
            if workset and not workset.IsOpen:
                findings.append(
                    Finding(
                        "workset_closed",
                        t(
                            "reason_workset_closed",
                            "Workset '{}' is closed (global setting)",
                        ).format(ws_name),
                    )
                )
            else:
                defaults = DB.WorksetDefaultVisibilitySettings.GetWorksetDefaultVisibilitySettings(
                    ctx.doc
                )
                if defaults and not defaults.IsWorksetVisible(ws_id):
                    findings.append(
                        Finding(
                            "workset_default_hidden",
                            t(
                                "reason_workset_default_hidden",
                                "Workset '{}' is hidden by the model's default"
                                " workset visibility setting",
                            ).format(ws_name),
                            fix=fix,
                        )
                    )
    except Exception:
        pass
    return findings


def _check_phase(ctx):
    """Phase filter hides the element's phase status in this view.

    Uses the official PhaseFilter / PhaseStatus mechanism, the only correct way
    to replicate Revit's logic; comparing raw phase sequence numbers breaks
    when the filter is configured to show demolished elements, for example.
    ``ElementOnPhaseStatus.None`` means the element has no phase data and is
    not subject to phase filtering.
    """
    view = ctx.view
    phase_param = view.get_Parameter(DB.BuiltInParameter.VIEW_PHASE)
    phase_id = phase_param.AsElementId() if phase_param else None
    if not _is_valid_id(phase_id):
        return []
    try:
        status = ctx.element.GetPhaseStatus(phase_id)
        if status == getattr(DB.ElementOnPhaseStatus, "None"):
            return []
        filter_param = view.get_Parameter(DB.BuiltInParameter.VIEW_PHASE_FILTER)
        filter_id = filter_param.AsElementId() if filter_param else None
        if not _is_valid_id(filter_id):
            return []
        phase_filter = ctx.doc.GetElement(filter_id)
        if (
            phase_filter
            and phase_filter.GetPhaseStatusPresentation(status)
            == DB.PhaseStatusPresentation.DontShow
        ):
            return [
                Finding(
                    "phase_filter",
                    t(
                        "reason_phase_filter",
                        "Hidden by phase filter (element phase status: '{}')",
                    ).format(status),
                )
            ]
    except Exception:
        pass
    return []


def _check_design_option(ctx):
    """Element belongs to a design option other than the one the view shows.

    ``element.DesignOption`` is not consistently exposed, so this reads the
    DESIGN_OPTION_ID parameter and compares it to VIEWER_OPTION_VISIBILITY.
    The design option API is limited and this may only work for plan views:
    https://forums.autodesk.com/t5/revit-api-forum/how-do-i-get-and-set-the-view-design-option-override/m-p/5209907
    https://forums.autodesk.com/t5/revit-ideas/api-to-get-set-view-overrides-for-design-options/idi-p/7891256
    """
    try:
        option_param = ctx.element.get_Parameter(DB.BuiltInParameter.DESIGN_OPTION_ID)
        option_id = (
            option_param.AsElementId()
            if option_param and option_param.HasValue
            else None
        )
        if not _is_valid_id(option_id):
            return []
        view_param = ctx.view.get_Parameter(
            DB.BuiltInParameter.VIEWER_OPTION_VISIBILITY
        )
        view_option_id = (
            view_param.AsElementId() if view_param and view_param.HasValue else None
        )
        if _is_valid_id(view_option_id) and view_option_id != option_id:
            option = ctx.doc.GetElement(option_id)
            return [
                Finding(
                    "design_option",
                    t(
                        "reason_design_option",
                        "Element belongs to design option '{}', which differs"
                        " from the option this view is displaying",
                    ).format(option.Name if option else option_id),
                )
            ]
    except Exception:
        pass
    return []


_IGNORED_STYLE_CATEGORIES = frozenset((int(DB.BuiltInCategory.OST_InvisibleLines),))


def _drawn_style_category_ids(element, view):
    """Return the (sub)category ids the element draws with in ``view``.

    Reads the element's geometry as the view presents it (detail level,
    symbolic lines such as structural stick symbols) and maps each piece to
    its graphics style category, or to the element's own category when the
    piece has no style. Invisible lines are ignored.

    Returns:
        (set[int] | None): category id values, or None when the view yields
        no styled geometry (e.g. annotations or empty geometry), in which
        case the caller cannot tell which subcategories matter.
    """
    category = element.Category
    if category is None:
        return None
    options = DB.Options()
    options.View = view
    try:
        geometry = element.get_Geometry(options)
    except Exception:
        return None
    if geometry is None:
        return None
    doc = element.Document
    own_category = id_value(category.Id)
    used = set()
    pending = [geometry]
    while pending:
        for item in pending.pop():
            if isinstance(item, DB.GeometryInstance):
                pending.append(item.GetInstanceGeometry())
                continue
            if isinstance(item, DB.GeometryElement):
                pending.append(item)
                continue
            if isinstance(item, DB.Solid) and item.Faces.Size == 0:
                continue
            style_id = item.GraphicsStyleId
            style = doc.GetElement(style_id) if _is_valid_id(style_id) else None
            style_category = style.GraphicsStyleCategory if style else None
            if style_category is None:
                used.add(own_category)
            elif id_value(style_category.Id) not in _IGNORED_STYLE_CATEGORIES:
                used.add(id_value(style_category.Id))
    return used or None


def _hidden_in_view(view, category_id_value):
    try:
        return view.GetCategoryHidden(DB.ElementId(category_id_value))
    except Exception:
        return False


def _drawn_subcategory_findings(ctx):
    """Confirmed subcategory causes from the geometry the element draws here.

    Returns:
        (list[Finding] | None): one finding per hidden (sub)category the
        element draws with, when everything it draws is hidden; an empty list
        when something it draws is visible; None when the drawn geometry
        cannot be read.
    """
    drawn = _drawn_style_category_ids(ctx.element, ctx.view)
    if drawn is None:
        return None
    if not all(_hidden_in_view(ctx.view, c) for c in drawn):
        return []
    findings = []
    for category_id_value in sorted(drawn):
        sub_category = DB.Category.GetCategory(ctx.doc, DB.ElementId(category_id_value))
        findings.append(
            Finding(
                "subcategory_hidden",
                t(
                    "reason_subcategory_drawn_hidden",
                    "Subcategory '{}' is hidden in this view, and everything"
                    " the element draws here uses hidden subcategories",
                ).format(sub_category.Name if sub_category else category_id_value),
                fix={"action": "unhide_category", "category_id": category_id_value},
            )
        )
    return findings


def _check_drawn_subcategories(ctx):
    """Confirmed subcategory causes only; safe to run on collector-visible elements.

    Note:
        Element collectors keep an element whose category is visible even
        when every subcategory it draws with is hidden (e.g. a column drawn
        only as "Stick Symbols" in a structural plan), so this runs like the
        clip checks, regardless of the collector's verdict.
    """
    category = ctx.element.Category
    if category is None or _hidden_in_view(ctx.view, id_value(category.Id)):
        return []
    return _drawn_subcategory_findings(ctx) or []


def _check_categories(ctx):
    """Element category, or the subcategories it draws with, hidden in the view.

    A hidden subcategory is a confirmed cause only when everything the element
    draws in this view uses hidden (sub)categories; if any drawn piece uses a
    visible one, hiding the others is not why the element is missing. When
    the drawn geometry cannot be read, every hidden subcategory of the
    element's category is reported as a speculative cause.
    """
    try:
        category = ctx.element.Category
    except Exception:
        category = None
    if not category:
        return []
    if _hidden_in_view(ctx.view, id_value(category.Id)):
        return [
            Finding(
                "category_hidden",
                t(
                    "reason_category_hidden",
                    "Category '{}' is hidden in this view",
                ).format(category.Name),
                fix={
                    "action": "unhide_category",
                    "category_id": id_value(category.Id),
                },
            )
        ]
    confirmed = _drawn_subcategory_findings(ctx)
    if confirmed is not None:
        return confirmed

    findings = []
    try:
        subcategories = list(category.SubCategories)
    except Exception:
        subcategories = []
    for subcategory in subcategories:
        if not _hidden_in_view(ctx.view, id_value(subcategory.Id)):
            continue
        findings.append(
            Finding(
                "subcategory_hidden",
                t(
                    "reason_subcategory_hidden",
                    "Subcategory '{}' of '{}' is hidden in this view"
                    " (element may belong to it)",
                ).format(subcategory.Name, category.Name),
                fix={
                    "action": "unhide_category",
                    "category_id": id_value(subcategory.Id),
                },
                speculative=True,
            )
        )
    return findings


def _check_element_hidden(ctx):
    findings = []
    try:
        if ctx.element.IsHidden(ctx.view):
            findings.append(
                Finding(
                    "element_hidden",
                    t(
                        "reason_element_hidden",
                        "Element is explicitly hidden in this view (Hide/Isolate)",
                    ),
                    fix={"action": "unhide_element"},
                )
            )
    except Exception:
        pass
    try:
        mode = DB.TemporaryViewMode.TemporaryHideIsolate
        if ctx.view.IsInTemporaryViewMode(
            mode
        ) and not ctx.view.IsElementVisibleInTemporaryViewMode(mode, ctx.element.Id):
            findings.append(
                Finding(
                    "temporary_hidden",
                    t(
                        "reason_temporary_hidden",
                        "Element is hidden by Temporary Hide/Isolate in this view",
                    ),
                    fix={"action": "reset_temporary_hide"},
                )
            )
    except Exception:
        pass
    return findings


def _filter_matches(ctx, filter_element):
    """Return True when a view filter applies to the element.

    A rule-based filter applies when the element's category is one of the
    filter's categories and the element passes its rules. Its
    ``GetElementFilter()`` holds the rules only, not the categories, and is
    None for a filter without rules, which then applies to every element of
    its categories. A selection filter applies to the ids it stores.
    """
    if isinstance(filter_element, DB.SelectionFilterElement):
        return filter_element.GetElementIds().Contains(ctx.element.Id)
    if not isinstance(filter_element, DB.ParameterFilterElement):
        return False
    category = ctx.element.Category
    if category is None or not filter_element.GetCategories().Contains(category.Id):
        return False
    rules = filter_element.GetElementFilter()
    return rules is None or rules.PassesFilter(ctx.doc, ctx.element.Id)


def _check_view_filters(ctx):
    """Enabled view filters set to invisible that apply to the element.

    Filters switched off with the view's "Enable Filter" checkbox are
    skipped: Revit ignores them, whatever their visibility setting.
    """
    view = ctx.view
    findings = []
    try:
        filter_ids = list(view.GetFilters())
    except Exception:
        return findings
    for filter_id in filter_ids:
        try:
            if view.GetFilterVisibility(filter_id):
                continue
            if hasattr(view, "GetIsFilterEnabled") and not view.GetIsFilterEnabled(
                filter_id
            ):
                continue
            filter_element = ctx.doc.GetElement(filter_id)
            if filter_element is None or not _filter_matches(ctx, filter_element):
                continue
            findings.append(
                Finding(
                    "view_filter",
                    t("reason_view_filter", "Hidden by view filter '{}'").format(
                        filter_element.Name
                    ),
                    fix={"action": "show_filter", "filter_id": id_value(filter_id)},
                )
            )
        except Exception:
            pass
    return findings


def _check_section_box(ctx):
    """Element entirely outside an active 3D section box.

    The section box clips independently of the crop box and lives in its own
    local space, so the element's world box is transformed into it first.
    """
    view = ctx.view
    try:
        if view.ViewType != DB.ViewType.ThreeD or not view.IsSectionBoxActive:
            return []
        section_box = view.GetSectionBox()
        bbox = ctx.world_bbox
        if section_box is None or bbox is None:
            return []
        low, high = local_extents(section_box.Transform, bbox)
        if (
            high.X < section_box.Min.X
            or low.X > section_box.Max.X
            or high.Y < section_box.Min.Y
            or low.Y > section_box.Max.Y
            or high.Z < section_box.Min.Z
            or low.Z > section_box.Max.Z
        ):
            return [
                Finding(
                    "section_box",
                    t(
                        "reason_section_box",
                        "Element bounding box is entirely outside the view's"
                        " active 3D section box",
                    ),
                    fix={"action": "expand_section_box"},
                )
            ]
    except Exception:
        pass
    return []


def _check_crop_region(ctx):
    """Element entirely outside the crop region.

    The crop box lives in view space (``CropBox.Transform``) while element
    boxes are in model space, so the element box is transformed into view
    space before the 2D overlap test. Perspective 3D crops are frustums and
    are skipped.

    Note:
        Element collectors can still report elements outside the crop: per
        the API, Revit "relies on later processing to eliminate the elements
        hidden by the crop". This check therefore also runs for elements the
        collector reported as visible.
    """
    view = ctx.view
    try:
        if not view.CropBoxActive:
            return []
        if isinstance(view, DB.View3D) and view.IsPerspective:
            return []
        bbox = ctx.world_bbox
        if bbox is None:
            return []
        crop = view.CropBox
        low, high = local_extents(crop.Transform, bbox)
        if (
            high.X < crop.Min.X - _TOLERANCE
            or low.X > crop.Max.X + _TOLERANCE
            or high.Y < crop.Min.Y - _TOLERANCE
            or low.Y > crop.Max.Y + _TOLERANCE
        ):
            return [
                Finding(
                    "crop_box",
                    t(
                        "reason_crop_box",
                        "Element bounding box is entirely outside the view crop region",
                    ),
                    fix={"action": "disable_crop"},
                )
            ]
    except Exception:
        pass
    return []


def _check_section_depth(ctx):
    """Element behind a section/elevation's cut plane or beyond its far clip.

    In crop-box space the view looks down -Z: the cut plane sits at
    ``CropBox.Max.Z`` and the far clip plane at ``CropBox.Min.Z``. The far
    plane only clips when VIEWER_BOUND_FAR_CLIPPING is not "No clip" (0).
    View-specific elements live in the view plane and are skipped.
    """
    view = ctx.view
    if not isinstance(view, DB.ViewSection) or ctx.is_view_specific:
        return []
    bbox = ctx.world_bbox
    if bbox is None:
        return []
    try:
        crop = view.CropBox
        low, high = local_extents(crop.Transform, bbox)
        if low.Z > crop.Max.Z + _TOLERANCE:
            return [
                Finding(
                    "behind_cut_plane",
                    t(
                        "reason_behind_cut_plane",
                        "Element is entirely behind the view's cut plane, so"
                        " the section/elevation does not look at it",
                    ),
                )
            ]
        far_param = view.get_Parameter(DB.BuiltInParameter.VIEWER_BOUND_FAR_CLIPPING)
        if (
            far_param
            and far_param.AsInteger() != 0
            and high.Z < crop.Min.Z - _TOLERANCE
        ):
            return [
                Finding(
                    "far_clip",
                    t(
                        "reason_far_clip",
                        "Element is beyond the view's far clip offset",
                    ),
                    fix={"action": "disable_far_clip"},
                )
            ]
    except Exception:
        pass
    return []


_SHOWN_ABOVE_CUT_FAMILY_CATEGORIES = frozenset(
    int(category)
    for category in (
        DB.BuiltInCategory.OST_Windows,
        DB.BuiltInCategory.OST_Casework,
        DB.BuiltInCategory.OST_GenericModel,
    )
)


def displays_above_cut_plane(element):
    """Return True when a plan view draws the element between cut and top.

    Per Autodesk's "About the View Range", elements entirely above the cut
    plane and below the top clip plane are not drawn unless they are windows,
    casework or generic models. Revit only applies that rule to cuttable
    categories: non-cuttable ones (ducts, pipes, lighting, mechanical
    equipment, ...) stay visible up to the top clip plane, as does a family
    whose "Enable Cutting in Views" is off.

    Note:
        Cuttability is read from the model's own Revit rather than a version
        table. Revit 2023 made Furniture, Furniture Systems, Plumbing Fixtures
        and Specialty Equipment cuttable, so on 2021/2022 those still report
        non-cuttable and remain visible above the cut, as they do there.
        The window/casework/generic model exception holds for family
        instances only; DirectShapes of those categories are hidden.
    """
    category = element.Category
    if category is None:
        return False
    if not category.IsCuttable:
        return True
    if not isinstance(element, DB.FamilyInstance):
        return False
    if id_value(category.Id) in _SHOWN_ABOVE_CUT_FAMILY_CATEGORIES:
        return True
    cutting_parameter = getattr(
        DB.BuiltInParameter, "FAMILY_ENABLE_CUTTING_IN_VIEWS", None
    )
    if cutting_parameter is None:
        return False
    try:
        enabled = element.Symbol.Family.get_Parameter(cutting_parameter)
        return enabled is not None and enabled.AsInteger() == 0
    except Exception:
        return False


def _check_view_range(ctx):
    """Element outside what a plan view's range draws.

    Flags elements fully above the upper bound, fully below the lower bound
    (see ``get_view_range_bounds``), and, in floor, area and structural
    plans, elements fully between the cut plane and the top that
    ``displays_above_cut_plane`` says Revit does not draw.

    Invariant:
        Only one finding offers a fix that moves planes upward. For an element
        Revit does not draw above the cut, extending the top would not help,
        so the cut plane fix replaces it.
    """
    view = ctx.view
    if not isinstance(view, DB.ViewPlan) or ctx.is_view_specific:
        return []
    bbox = ctx.world_bbox
    if bbox is None:
        return []
    findings = []
    try:
        is_rcp = view.ViewType == DB.ViewType.CeilingPlan
        lower, upper = get_view_range_bounds(ctx.doc, view)
        cut = None
        if not is_rcp:
            cut = resolve_view_range_elevation(
                ctx.doc, view.GetViewRange(), DB.PlanViewPlane.CutPlane
            )
        hidden_above_cut = (
            cut is not None
            and bbox.Min.Z > cut
            and not displays_above_cut_plane(ctx.element)
        )
        if upper is not None and bbox.Min.Z > upper:
            findings.append(
                Finding(
                    "viewrange_above",
                    t(
                        "reason_viewrange_above",
                        "Element is above the view range top clip plane"
                        " (element min Z {:.3f} ft > top {:.3f} ft)",
                    ).format(bbox.Min.Z, upper),
                    fix=None
                    if hidden_above_cut
                    else {"action": "extend_view_range", "direction": "up"},
                )
            )
        if hidden_above_cut:
            category = ctx.element.Category
            findings.append(
                Finding(
                    "above_cut_plane",
                    t(
                        "reason_above_cut_plane",
                        "Element is entirely above the cut plane (element min Z"
                        " {:.3f} ft > cut {:.3f} ft). Between the cut plane and"
                        " the top, plan views only draw windows, casework,"
                        " generic models and non-cuttable categories; '{}' is"
                        " cuttable",
                    ).format(bbox.Min.Z, cut, category.Name if category else "?"),
                    fix={"action": "raise_cut_plane"},
                )
            )
        if lower is not None and bbox.Max.Z < lower:
            findings.append(
                Finding(
                    "viewrange_below",
                    t(
                        "reason_viewrange_below",
                        "Element is below the view range's lower bound (bottom"
                        " clip / view depth) (element max Z {:.3f} ft < lower"
                        " bound {:.3f} ft)",
                    ).format(bbox.Max.Z, lower),
                    fix=None
                    if is_rcp
                    else {"action": "extend_view_range", "direction": "down"},
                )
            )
    except Exception:
        pass
    return findings


def _check_view_specific(ctx):
    """View-specific element owned by another view can never appear here."""
    try:
        owner_id = ctx.element.OwnerViewId
        if _is_valid_id(owner_id) and owner_id != ctx.view.Id:
            owner = ctx.doc.GetElement(owner_id)
            return [
                Finding(
                    "view_specific",
                    t(
                        "reason_view_specific",
                        "Element is view-specific and belongs to another view"
                        " ('{}'), so it cannot appear here",
                    ).format(owner.Name if owner else owner_id),
                    fix={"action": "open_view", "view_id": id_value(owner_id)},
                )
            ]
    except Exception:
        pass
    return []


def _check_view_template(ctx):
    """Applied view template (informational): it may lock the settings above."""
    try:
        template_id = ctx.view.ViewTemplateId
        if _is_valid_id(template_id):
            template = ctx.doc.GetElement(template_id)
            return [
                Finding(
                    "view_template",
                    t(
                        "reason_view_template",
                        "View template '{}' is applied - some visibility"
                        " settings may be locked and must be changed in the"
                        " template",
                    ).format(template.Name if template else template_id),
                    informational=True,
                )
            ]
    except Exception:
        pass
    return []


def _check_view_discipline(ctx):
    """Non-coordination view discipline (informational).

    Revit shows or hides some categories automatically by discipline,
    independent of Visibility/Graphics, and there is no public API to ask
    whether a specific category is discipline-filtered.
    More: https://www.modelical.com/en/revit-view-discipline/
    """
    try:
        discipline = ctx.view.Discipline
        if discipline != DB.ViewDiscipline.Coordination:
            return [
                Finding(
                    "view_discipline",
                    t(
                        "reason_view_discipline",
                        "View discipline is set to '{}' - some categories are"
                        " shown or hidden automatically based on discipline,"
                        " independent of Visibility/Graphics settings",
                    ).format(discipline),
                    informational=True,
                    fix={"action": "set_discipline_coordination"},
                )
            ]
    except Exception:
        pass
    return []


_SETTING_CHECKS = (
    _check_workset,
    _check_phase,
    _check_design_option,
    _check_categories,
    _check_element_hidden,
    _check_view_filters,
    _check_section_box,
)

_CLIP_CHECKS = (
    _check_crop_region,
    _check_section_depth,
)

_TRAILING_CHECKS = (
    _check_view_range,
    _check_view_specific,
    _check_view_template,
    _check_view_discipline,
)


def diagnose(element, view, visible_ids=None):
    """Explain why ``element`` is not visible in ``view``.

    Args:
        element (DB.Element): element to diagnose.
        view (DB.View): view in the same document.
        visible_ids (set[int] | None): result of ``collect_visible_ids`` for
            the view; collected on the fly when omitted.

    Returns:
        (list[Finding]): empty when the element is visible. Otherwise at least
        one non-informational finding; an "unknown" finding is added when no
        specific cause could be pinned down.

    Note:
        When the view's collector reports the element, only the checks the
        collector is blind to run: crop and cut-plane clipping, and confirmed
        hidden subcategories. Any such finding overrides the collector.
    """
    ctx = _CheckContext(element, view)
    if visible_ids is None:
        visible_ids = collect_visible_ids(view)

    clip_findings = []
    for check in _CLIP_CHECKS:
        clip_findings.extend(check(ctx))

    if ctx.element_id in visible_ids:
        blind_findings = clip_findings + _check_drawn_subcategories(ctx)
        if not blind_findings:
            return []
        return blind_findings + _check_view_template(ctx)

    findings = []
    for check in _SETTING_CHECKS:
        findings.extend(check(ctx))
    findings.extend(clip_findings)
    for check in _TRAILING_CHECKS:
        findings.extend(check(ctx))

    if all(f.informational for f in findings):
        findings.append(
            Finding(
                "unknown",
                t(
                    "reason_unknown",
                    "Element is not visible but no specific cause could be"
                    " determined. Possible causes: view-specific element type"
                    " (e.g. annotation from another view), linked model"
                    " visibility, or detail level.",
                ),
            )
        )
    return findings


def diagnose_invisibility(element, view, visible_ids=None):
    """Explain why ``element`` is not visible in ``view`` as plain strings.

    Compatibility wrapper around ``diagnose``.

    Returns:
        (tuple[list[str], list[str]]): localized reasons and a parallel list
        of short English codes (for grouping/logging); both empty when the
        element is visible.
    """
    findings = diagnose(element, view, visible_ids)
    return (
        [f.message for f in findings],
        [LEGACY_SHORT_CODES.get(f.code, f.code) for f in findings],
    )
