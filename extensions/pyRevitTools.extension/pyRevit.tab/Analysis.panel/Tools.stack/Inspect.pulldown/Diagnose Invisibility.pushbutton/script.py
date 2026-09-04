# -*- coding: utf-8 -*-
"""Diagnose why the selected/picked element(s) are not visible in a
chosen view, and print a per-element report of the reason(s)."""

from pyrevit import revit, forms, script
from pyrevit import DB
from pyrevit.coreutils import applocales
from pyrevit.revit import query
from pyrevit.compat import get_elementid_value_func

logger = script.get_logger()
output = script.get_output()

get_elementid_value = get_elementid_value_func()

# Nominal base path -- this file does not need to exist. applocales derives
# the sibling resource-dictionary filenames from it:
#   resources.ResourceDictionary.<locale>.xaml
_RESX_BASE = script.get_bundle_file("resources.xaml")


def _t(key, default=None):
    """Look up a localized UI string for the current pyRevit / Revit
    language, falling back to en_us and then to `default`.

    Args:
        key: resource key (x:Key in the ResourceDictionary files)
        default: value to use if the key isn't found in any locale file

    Returns:
        str: localized string, `default`, or `key` if no default given
    """
    result = applocales.get_locale_string_from_xaml(_RESX_BASE, key)
    if result == key and default is not None:
        return default
    return result


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_workset_name(element):
    doc = element.Document
    if not doc.IsWorkshared:
        return "N/A"
    try:
        ws_param = element.get_Parameter(DB.BuiltInParameter.ELEM_PARTITION_PARAM)
        if ws_param:
            ws_id = DB.WorksetId(ws_param.AsInteger())
            ws = doc.GetWorksetTable().GetWorkset(ws_id)
            return ws.Name if ws else "Unknown"
    except Exception:
        pass
    return "N/A"


def _get_workset_id(element):
    doc = element.Document
    if not doc.IsWorkshared:
        return None
    try:
        ws_param = element.get_Parameter(DB.BuiltInParameter.ELEM_PARTITION_PARAM)
        if ws_param:
            return DB.WorksetId(ws_param.AsInteger())
    except Exception:
        pass
    return None


def _get_level_elevation(doc, level_id):
    """Return the raw elevation of a Level element, or None."""
    if level_id is None or level_id == DB.ElementId.InvalidElementId:
        return None
    try:
        level = doc.GetElement(level_id)
        if level and hasattr(level, "Elevation"):
            return level.Elevation
    except Exception:
        pass
    return None


def _resolve_view_range_elevation(doc, view_range, plane):
    """
    Resolve a PlanViewPlane to an absolute project elevation (feet).
    Returns None when the plane is set to "Unlimited" or cannot be resolved.
    """
    try:
        level_id = view_range.GetLevelId(plane)
        offset = view_range.GetOffset(plane)
        base = _get_level_elevation(doc, level_id)
        if base is not None:
            return base + offset
    except Exception:
        pass
    return None


def _get_view_range_bounds(doc, view):
    """
    Return (lower_elev, upper_elev) absolute project elevations for a plan
    view. Either value may be None if the plane is set to Unlimited or
    unresolvable.

    For FloorPlan / AreaPlan / EngineeringPlan: "lower_elev" is the lower
    of the bottom clip plane and the view depth plane. The view depth
    plane can extend further DOWN than the bottom clip plane - elements
    between the two still render (dashed), so only elements below BOTH
    should be flagged as out of range. "upper_elev" is simply the top
    clip plane.

    For CeilingPlan (RCP), the relationship flips per Autodesk's
    documented view range behavior: the Cut Plane is coincident with the
    Bottom Clip Plane (Bottom is disabled/grayed out in the view range
    dialog for RCPs), and it's the View Depth plane that can extend
    further UP than the Top clip plane instead - elements between the two
    still render (dashed). So for CeilingPlan, "upper_elev" is the higher
    of the top clip plane and the view depth plane, and "lower_elev" is
    simply the bottom/cut plane.
    """
    try:
        vr = view.GetViewRange()
        top = _resolve_view_range_elevation(doc, vr, DB.PlanViewPlane.TopClipPlane)
        bot = _resolve_view_range_elevation(doc, vr, DB.PlanViewPlane.BottomClipPlane)
        depth = _resolve_view_range_elevation(doc, vr, DB.PlanViewPlane.ViewDepthPlane)

        if view.ViewType == DB.ViewType.CeilingPlan:
            # RCP: Cut Plane == Bottom Clip Plane (disabled/synced), and
            # View Depth extends upward past Top rather than downward
            # past Bottom.
            upper_candidates = [v for v in (top, depth) if v is not None]
            upper = max(upper_candidates) if upper_candidates else None
            lower = bot
        else:
            lower_candidates = [v for v in (bot, depth) if v is not None]
            lower = min(lower_candidates) if lower_candidates else None
            upper = top

        return lower, upper
    except Exception:
        pass
    return None, None


def _subcategory_ids_for_category(category):
    """
    Yield the ElementIds of all direct subcategories of a Category object.
    Works with both old and new pyRevit/Revit API versions.
    """
    try:
        for sub in category.SubCategories:
            yield sub.Id
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def diagnose_invisibility(element, view, visible_ids=None):
    """
    Return a list of human-readable strings explaining why *element* is not
    visible in *view*.  Returns an empty list when the element IS visible.
    Optional argument for visible_ids if they have been pre-collected earlier.

    Checks performed (in order):
        1.  Workset hidden / closed / hidden by default visibility setting
        2.  Phase filter (via PhaseStatus)
        3.  Design option mismatch
        4.  Category hidden in view
        5.  Subcategory hidden in view
        6.  Element explicitly hidden in view
        7.  View filters that hide the element
        8.  Crop region / 3D section box (element outside bounds)
        9.  View range / clip planes (plan views only, incl. view depth)
        10. View template active (informational - may lock visibility settings)
        11. View-specific element belonging to another view
        12. View discipline (informational - some categories are shown or
            hidden automatically based on discipline)

    Args:
        element: A Revit Element object.
        view:    A Revit View object (must be in the same document).

    Returns:
        (reasons, reasons_short) - reasons is a list[str], empty when the
        element is visible, otherwise one or more localized reasons ("Hidden
        - reason unknown" style entry if the cause can't be pinned down).
        reasons_short is a parallel list of short, English, internal codes
        (not localized - not shown to the user, useful for grouping/logging).
    """
    eid = get_elementid_value(element.Id)
    doc = element.Document

    # ------------------------------------------------------------------
    # Fast-path: if already visible, return immediately.
    # Collecting all visible IDs upfront also provides the authoritative
    # "is it actually hidden?" test, because Revit's own collector
    # filters out everything not rendered in the view.
    # ------------------------------------------------------------------
    if visible_ids is None:
        visible_ids = set(
            get_elementid_value(e.Id) for e in query.get_all_elements_in_view(view)
        )
    if eid in visible_ids:
        return [], []

    reasons = []
    reasons_short = []

    # ------------------------------------------------------------------
    # 1. Workset
    # ------------------------------------------------------------------
    if doc.IsWorkshared:
        ws_id = _get_workset_id(element)
        if ws_id:
            try:
                vis = view.GetWorksetVisibility(ws_id)
                ws_name = _get_workset_name(element)
                if vis == DB.WorksetVisibility.Hidden:
                    reasons.append(
                        _t(
                            "reason_workset_hidden",
                            "Workset '{}' is explicitly hidden in this view",
                        ).format(ws_name)
                    )
                    reasons_short.append("Workset hidden")
                elif vis == DB.WorksetVisibility.UseGlobalSetting:
                    ws = doc.GetWorksetTable().GetWorkset(ws_id)
                    if ws and not ws.IsOpen:
                        reasons.append(
                            _t(
                                "reason_workset_closed",
                                "Workset '{}' is closed (global setting)",
                            ).format(ws_name)
                        )
                        reasons_short.append("Workset closed")
                    else:
                        # A workset can be OPEN and still be hidden by the
                        # model's default workset visibility setting - IsOpen
                        # alone does not tell us that. Check the real source.
                        try:
                            default_vis = DB.WorksetDefaultVisibilitySettings.GetWorksetDefaultVisibilitySettings(
                                doc
                            )
                            if default_vis and not default_vis.IsWorksetVisible(ws_id):
                                reasons.append(
                                    _t(
                                        "reason_workset_default_hidden",
                                        "Workset '{}' is hidden by the model's"
                                        " default workset visibility setting",
                                    ).format(ws_name)
                                )
                                reasons_short.append("Workset default hidden")
                        except Exception:
                            pass
            except Exception:
                pass

    # ------------------------------------------------------------------
    # 2. Phase  -  use the official PhaseFilter / PhaseStatus mechanism.
    #
    #    element.GetPhaseStatus(phase_id) returns one of:
    #        PhaseStatus.New, Existing, Temporary, Demolished, None
    #
    #    The view's PhaseFilter then decides whether each status is shown.
    #    This is the only correct way to replicate Revit's own logic;
    #    comparing raw sequence numbers is unreliable when the filter
    #    is configured to show demolished elements, for example.
    # ------------------------------------------------------------------
    view_phase_param = view.get_Parameter(DB.BuiltInParameter.VIEW_PHASE)
    view_phase_id = (
        view_phase_param.AsElementId()
        if view_phase_param
        else DB.ElementId.InvalidElementId
    )

    if view_phase_id and view_phase_id != DB.ElementId.InvalidElementId:
        try:
            phase_status = element.GetPhaseStatus(view_phase_id)
            # ElementOnPhaseStatus.None means the element has no phase data
            # and is not subject to phase filtering.
            if phase_status != getattr(DB.ElementOnPhaseStatus, "None"):
                pf_param = view.get_Parameter(DB.BuiltInParameter.VIEW_PHASE_FILTER)
                pf_id = (
                    pf_param.AsElementId()
                    if pf_param
                    else DB.ElementId.InvalidElementId
                )
                if pf_id and pf_id != DB.ElementId.InvalidElementId:
                    phase_filter = doc.GetElement(pf_id)
                    if phase_filter:
                        presentation = phase_filter.GetPhaseStatusPresentation(
                            phase_status
                        )
                        if presentation == DB.PhaseStatusPresentation.DontShow:
                            reasons.append(
                                _t(
                                    "reason_phase_filter",
                                    "Hidden by phase filter"
                                    " (element phase status: '{}')",
                                ).format(phase_status)
                            )
                            reasons_short.append("Phase Filter")
        except Exception:
            logger.exception("Error evaluating phase status for element {}".format(eid))

    # ------------------------------------------------------------------
    # 3. Design Option
    #    element.DesignOption is unreliable / not consistently exposed.
    #    Instead read the DESIGN_OPTION_ID built-in parameter directly off
    #    the element, and compare it against VIEWER_OPTION_VISIBILITY on
    #    the view (the option the view is currently displaying). If the
    #    element is assigned to an option and the view is showing a
    #    *different* option, the element cannot appear here.
    #
    #    Design Option API is pretty bad. This may only work for plan views.
    #    Relevant discussions:
    #    https://forums.autodesk.com/t5/revit-api-forum/how-do-i-get-and-set-the-view-design-option-override/m-p/5209907/highlight/false#M6995
    #    https://forums.autodesk.com/t5/revit-ideas/api-to-get-set-view-overrides-for-design-options/idi-p/7891256
    # ------------------------------------------------------------------
    try:
        do_param = element.get_Parameter(DB.BuiltInParameter.DESIGN_OPTION_ID)
        elem_option_id = (
            do_param.AsElementId()
            if do_param and do_param.HasValue
            else DB.ElementId.InvalidElementId
        )
        if elem_option_id and elem_option_id != DB.ElementId.InvalidElementId:
            view_option_param = view.get_Parameter(
                DB.BuiltInParameter.VIEWER_OPTION_VISIBILITY
            )
            view_option_id = (
                view_option_param.AsElementId()
                if view_option_param and view_option_param.HasValue
                else DB.ElementId.InvalidElementId
            )
            elem_option = doc.GetElement(elem_option_id)
            elem_option_name = elem_option.Name if elem_option else str(elem_option_id)
            if (
                view_option_id
                and view_option_id != DB.ElementId.InvalidElementId
                and view_option_id != elem_option_id
            ):
                reasons.append(
                    _t(
                        "reason_design_option",
                        "Element belongs to design option '{}', which differs"
                        " from the option this view is displaying",
                    ).format(elem_option_name)
                )
                reasons_short.append("Design Option")
    except Exception:
        pass

    # ------------------------------------------------------------------
    # 4. Category hidden in view
    # ------------------------------------------------------------------
    elem_category = None
    try:
        elem_category = element.Category
        if elem_category:
            if view.GetCategoryHidden(elem_category.Id):
                reasons.append(
                    _t(
                        "reason_category_hidden", "Category '{}' is hidden in this view"
                    ).format(elem_category.Name)
                )
                reasons_short.append("Category")
    except Exception:
        pass

    # ------------------------------------------------------------------
    # 5. Subcategory hidden in view
    #    Iterate over all subcategories of the element's parent category
    #    and report any that are hidden.  We cannot reliably know which
    #    specific subcategory an arbitrary element belongs to without
    #    element-type-specific introspection, so we report ALL hidden
    #    subcategories as potential contributors.
    # ------------------------------------------------------------------
    if elem_category:
        try:
            for sub_id in _subcategory_ids_for_category(elem_category):
                try:
                    if view.GetCategoryHidden(sub_id):
                        sub_cat = doc.GetElement(sub_id)
                        sub_name = sub_cat.Name if sub_cat else str(sub_id)
                        reasons.append(
                            _t(
                                "reason_subcategory_hidden",
                                "Subcategory '{}' of '{}' is hidden in this view"
                                " (element may belong to it)",
                            ).format(sub_name, elem_category.Name)
                        )
                        reasons_short.append("Subcategory")
                except Exception:
                    pass
        except Exception:
            pass

    # ------------------------------------------------------------------
    # 6. Element explicitly hidden in view
    # ------------------------------------------------------------------
    try:
        if element.IsHidden(view):
            reasons.append(
                _t(
                    "reason_element_hidden",
                    "Element is explicitly hidden in this view (Hide/Isolate)",
                )
            )
            reasons_short.append("Hidden")
    except Exception:
        pass

    # ------------------------------------------------------------------
    # 7. View Filters
    #    For each filter applied to the view that overrides visibility to
    #    False, check whether the filter's rules actually match this element
    #    using ElementFilter.PassesFilter - the same test Revit performs.
    # ------------------------------------------------------------------
    try:
        for filter_id in view.GetFilters():
            try:
                if not view.GetFilterVisibility(filter_id):
                    rule_filter = doc.GetElement(filter_id)
                    if rule_filter and hasattr(rule_filter, "GetElementFilter"):
                        elem_filter = rule_filter.GetElementFilter()
                        if elem_filter and elem_filter.PassesFilter(doc, element.Id):
                            reasons.append(
                                _t(
                                    "reason_view_filter", "Hidden by view filter '{}'"
                                ).format(rule_filter.Name)
                            )
                            reasons_short.append("Viewfilter")
            except Exception:
                pass
    except Exception:
        pass

    # ------------------------------------------------------------------
    # 8a. 3D Section Box
    #     For View3D with an active section box, that box clips geometry
    #     independently of CropBox and is not expressed in view space, so
    #     it needs its own full 3-D overlap test against the world bbox
    #     transformed into the section box's local coordinate space.
    # ------------------------------------------------------------------
    try:
        if view.ViewType == DB.ViewType.ThreeD and getattr(
            view, "IsSectionBoxActive", False
        ):
            section_box = view.GetSectionBox()
            world_bbox = element.get_BoundingBox(None)
            if world_bbox is not None and section_box is not None:
                try:
                    inverse = section_box.Transform.Inverse
                    corners = [
                        DB.XYZ(x, y, z)
                        for x in (world_bbox.Min.X, world_bbox.Max.X)
                        for y in (world_bbox.Min.Y, world_bbox.Max.Y)
                        for z in (world_bbox.Min.Z, world_bbox.Max.Z)
                    ]
                    local_pts = [inverse.OfPoint(c) for c in corners]
                    lmin_x = min(p.X for p in local_pts)
                    lmax_x = max(p.X for p in local_pts)
                    lmin_y = min(p.Y for p in local_pts)
                    lmax_y = max(p.Y for p in local_pts)
                    lmin_z = min(p.Z for p in local_pts)
                    lmax_z = max(p.Z for p in local_pts)
                    outside_section = (
                        lmax_x < section_box.Min.X
                        or lmin_x > section_box.Max.X
                        or lmax_y < section_box.Min.Y
                        or lmin_y > section_box.Max.Y
                        or lmax_z < section_box.Min.Z
                        or lmin_z > section_box.Max.Z
                    )
                    if outside_section:
                        reasons.append(
                            _t(
                                "reason_section_box",
                                "Element bounding box is entirely outside the"
                                " view's active 3D section box",
                            )
                        )
                        reasons_short.append("SectionBox")
                except Exception:
                    pass
    except Exception:
        pass

    # ------------------------------------------------------------------
    # 8b. Crop Region
    #    The element's bounding box (in view coordinates) must overlap
    #    the crop box.  Both boxes are expressed in view space so a simple
    #    2-D overlap test in X/Y is sufficient.
    # ------------------------------------------------------------------
    try:
        if view.CropBoxActive:
            crop = view.CropBox  # BoundingBoxXYZ in view coordinates
            bbox = element.get_BoundingBox(view)
            if bbox is not None:
                outside = (
                    bbox.Max.X < crop.Min.X
                    or bbox.Min.X > crop.Max.X
                    or bbox.Max.Y < crop.Min.Y
                    or bbox.Min.Y > crop.Max.Y
                )
                if outside:
                    reasons.append(
                        _t(
                            "reason_crop_box",
                            "Element bounding box is entirely outside the"
                            " view crop region",
                        )
                    )
                    reasons_short.append("CropBox")
            # bbox == None means Revit has no geometric extents for this element
            # in this view - treat it as a potential issue only when crop is active.
    except Exception:
        pass

    # ------------------------------------------------------------------
    # 9. View Range  (plan views only)
    #    Compare the element's world-space Z extents against the resolved
    #    top clip plane and the lower bound (the lower of the bottom clip
    #    plane and the view depth plane - see _get_view_range_bounds).
    #    Only flags when we can confirm the element is fully above or
    #    fully below the range.
    # ------------------------------------------------------------------
    try:
        if isinstance(view, DB.ViewPlan):
            bot_elev, top_elev = _get_view_range_bounds(doc, view)
            # Use the bounding box in world (None view) coordinates for Z
            world_bbox = element.get_BoundingBox(None)
            if world_bbox is not None:
                elem_min_z = world_bbox.Min.Z
                elem_max_z = world_bbox.Max.Z
                if top_elev is not None and elem_min_z > top_elev:
                    reasons.append(
                        _t(
                            "reason_viewrange_above",
                            "Element is above the view range top clip plane"
                            " (element min Z {:.3f} ft > top {:.3f} ft)",
                        ).format(elem_min_z, top_elev)
                    )
                    reasons_short.append("Viewrange")
                if bot_elev is not None and elem_max_z < bot_elev:
                    reasons.append(
                        _t(
                            "reason_viewrange_below",
                            "Element is below the view range's lower bound"
                            " (bottom clip / view depth) (element max Z {:.3f} ft"
                            " < lower bound {:.3f} ft)",
                        ).format(elem_max_z, bot_elev)
                    )
                    reasons_short.append("Viewrange")
    except Exception:
        pass

    # ------------------------------------------------------------------
    # 10. View Template  (informational)
    #     A template locks visibility settings, so the user may be unable
    #     to unhide the element from within the view.  We flag this so
    #     they know where to look if the above fixes don't work.
    # ------------------------------------------------------------------
    try:
        tmpl_id = view.ViewTemplateId
        if tmpl_id and tmpl_id != DB.ElementId.InvalidElementId:
            tmpl = doc.GetElement(tmpl_id)
            tmpl_name = tmpl.Name if tmpl else str(tmpl_id)
            reasons.append(
                _t(
                    "reason_view_template",
                    "View template '{}' is applied - some visibility settings"
                    " may be locked and must be changed in the template",
                ).format(tmpl_name)
            )
            reasons_short.append("Viewtemplate")
    except Exception:
        pass

    # ------------------------------------------------------------------
    # 11. View-specific element (detail items / annotations)
    #     Some elements (detail lines, filled regions, text notes, etc.)
    #     belong to a single view via OwnerViewId. If that owner view is
    #     not the one being inspected, the element cannot appear here at
    #     all, regardless of any other visibility setting.
    # ------------------------------------------------------------------
    try:
        owner_view_id = element.OwnerViewId
        if owner_view_id and owner_view_id != DB.ElementId.InvalidElementId:
            if owner_view_id != view.Id:
                owner_view = doc.GetElement(owner_view_id)
                owner_view_name = owner_view.Name if owner_view else str(owner_view_id)
                reasons.append(
                    _t(
                        "reason_view_specific",
                        "Element is view-specific and belongs to another view"
                        " ('{}'), so it cannot appear here",
                    ).format(owner_view_name)
                )
                reasons_short.append("View-specific")
    except Exception:
        pass

    # ------------------------------------------------------------------
    # 12. View Discipline  (informational)
    #     Certain model categories are automatically shown or hidden by
    #     Revit based on the view's Discipline setting (e.g. some
    #     structural/MEP-only categories, and some architectural-only
    #     categories), independent of the Visibility/Graphics overrides
    #     checked above. Not every view type exposes Discipline, and
    #     there's no public API to ask "is this specific category
    #     discipline-filtered", so - like the view template check above -
    #     this is reported as informational context rather than a
    #     confirmed cause.
    #     More: https://www.modelical.com/en/revit-view-discipline/
    # ------------------------------------------------------------------
    try:
        discipline = view.Discipline
        if discipline != DB.ViewDiscipline.Coordination:
            reasons.append(
                _t(
                    "reason_view_discipline",
                    "View discipline is set to '{}' - some categories are"
                    " shown or hidden automatically based on discipline,"
                    " independent of Visibility/Graphics settings",
                ).format(discipline)
            )
            reasons_short.append("Discipline")
    except Exception:
        pass

    # ------------------------------------------------------------------
    # Fallback
    # ------------------------------------------------------------------
    if not reasons:
        reasons.append(
            _t(
                "reason_unknown",
                "Element is not visible but no specific cause could be"
                " determined. Possible causes: view-specific element type"
                " (e.g. annotation from another view), linked model"
                " visibility, or detail level.",
            )
        )
        reasons_short.append("Hidden unknown")

    return reasons, reasons_short


# ---------------------------------------------------------------------------
# UI / entry point
# ---------------------------------------------------------------------------


def _get_target_elements():
    """Elements to diagnose: current selection if non-empty, otherwise
    prompt the user to pick element(s). Returns [] if nothing is selected
    and the pick is cancelled."""
    selection = revit.get_selection()
    if selection and len(selection) > 0:
        return list(selection.elements)
    elements = revit.pick_elements()
    return elements


def _format_element_label(element):
    try:
        cat_name = element.Category.Name if element.Category else "?"
    except Exception:
        cat_name = "?"
    try:
        elem_name = element.Name
    except Exception:
        elem_name = ""
    eid = get_elementid_value(element.Id)
    if elem_name:
        return "{} - {} (id {})".format(cat_name, elem_name, eid)
    return "{} (id {})".format(cat_name, eid)


def main():
    elements = _get_target_elements()
    if not elements:
        forms.alert(_t("no_elements_error", "No elements selected or picked."))
        return

    views = forms.select_views(
        title=_t("select_view_title", "Select View"),
        button_name=_t("select_view_button", "Diagnose in this View"),
    )
    if not views:
        forms.alert(_t("no_view_error", "No view selected."))
        return

    output.print_md("## {}".format(_t("report_title", "Visibility Diagnosis")))

    visible_count = 0
    hidden_count = 0

    for view in views:
        # Collect the visible-element set once per view and reuse it for every
        # element - this is the expensive part of diagnose_invisibility().
        visible_ids = set(
            get_elementid_value(e.Id) for e in query.get_all_elements_in_view(view)
        )

        view_link = output.linkify(view.Id, title=view.Name)
        output.print_md(view_link)

        for element in elements:
            try:
                label = _format_element_label(element)
                link = output.linkify(element.Id, title=label)
                reasons, _reasons_short = diagnose_invisibility(
                    element, view, visible_ids
                )

                if not reasons:
                    visible_count += 1
                    output.print_md(
                        "**{}** {}".format(
                            link, _t("status_visible", "Visible in this view.")
                        )
                    )
                else:
                    hidden_count += 1
                    output.print_md(
                        "**{}** {}".format(
                            link, _t("status_hidden", "NOT visible in this view:")
                        )
                    )
                    for reason in reasons:
                        output.print_md("- {}".format(reason))
            except Exception as ex:
                logger.exception(
                    "Error diagnosing element {}".format(
                        get_elementid_value(element.Id)
                    )
                )
                output.print_md(
                    "- {} `{}`: {}".format(
                        _t("status_error", "Error diagnosing element"),
                        get_elementid_value(element.Id),
                        ex,
                    )
                )

        output.insert_divider()

    output.print_md(
        _t("summary_line", "{} visible, {} not visible.").format(
            visible_count, hidden_count
        )
    )


if __name__ == "__main__":
    main()
