# -*- coding: utf-8 -*-
"""Fix actions for findings reported by ``invisibility_checks``.

A fix descriptor is a dict with an ``action`` key plus id-valued arguments.
``describe`` turns one into a button label for a given view, ``apply`` runs it.

Important:
    Settings a view template controls cannot be changed on the view itself.
    Fixes for those settings target the template instead, which changes every
    view using it; ``describe`` names the template so the user sees that
    before clicking.

Warning:
    ``apply`` must run in Revit API context. Each call is one named
    transaction, so every fix is a single undo step.
"""

from pyrevit import DB
from pyrevit.framework import List

from invisibility_checks import (
    get_view_range_bounds,
    id_value,
    local_extents,
    resolve_view_range_elevation,
    t,
)


_MARGIN_FT = 1.0

_LABELS = {
    "show_workset": ("fix_show_workset", "Show workset"),
    "unhide_category": ("fix_unhide_category", "Unhide category"),
    "unhide_element": ("fix_unhide_element", "Unhide element"),
    "reset_temporary_hide": ("fix_reset_temporary", "Reset temporary hide/isolate"),
    "show_filter": ("fix_show_filter", "Make filter visible"),
    "expand_section_box": ("fix_expand_section_box", "Expand section box"),
    "disable_crop": ("fix_disable_crop", "Disable crop region"),
    "disable_far_clip": ("fix_disable_far_clip", "Disable far clipping"),
    "extend_view_range": ("fix_extend_view_range", "Extend view range"),
    "raise_cut_plane": ("fix_raise_cut_plane", "Raise cut plane above element"),
    "set_discipline_coordination": (
        "fix_set_discipline",
        "Set discipline to Coordination",
    ),
    "open_view": ("fix_open_owner_view", "Open owner view"),
}

NAVIGATION_ACTIONS = frozenset(("open_view",))


class FixError(Exception):
    """A fix could not be applied; the message is shown to the user."""


def _element_id(value):
    return DB.ElementId(int(value))


def _category_template_parameter(doc, category_id):
    category = DB.Category.GetCategory(doc, category_id)
    if category is not None and category.Parent is not None:
        category = category.Parent
    category_type = category.CategoryType if category else None
    if category_type == DB.CategoryType.Annotation:
        return DB.BuiltInParameter.VIS_GRAPHICS_ANNOTATION
    if category_type == DB.CategoryType.AnalyticalModel:
        return DB.BuiltInParameter.VIS_GRAPHICS_ANALYTICAL_MODEL
    if category is not None and category.Id == DB.ElementId(
        DB.BuiltInCategory.OST_ImportObjectStyles
    ):
        return DB.BuiltInParameter.VIS_GRAPHICS_IMPORT
    return DB.BuiltInParameter.VIS_GRAPHICS_MODEL


def _template_parameter(view, fix):
    """Return the template-controllable parameter a fix touches, or None."""
    action = fix.get("action")
    if action == "unhide_category":
        return _category_template_parameter(
            view.Document, _element_id(fix["category_id"])
        )
    return {
        "show_filter": DB.BuiltInParameter.VIS_GRAPHICS_FILTERS,
        "show_workset": DB.BuiltInParameter.VIS_GRAPHICS_WORKSETS,
        "extend_view_range": DB.BuiltInParameter.PLAN_VIEW_RANGE,
        "raise_cut_plane": DB.BuiltInParameter.PLAN_VIEW_RANGE,
        "set_discipline_coordination": DB.BuiltInParameter.VIEW_DISCIPLINE,
        "disable_far_clip": DB.BuiltInParameter.VIEWER_BOUND_FAR_CLIPPING,
    }.get(action)


def settings_owner(view, fix):
    """Return the view or the view template that owns the setting a fix edits.

    A template owns a setting when it is applied to the view and the
    setting's parameter is not in the template's non-controlled list.
    """
    parameter = _template_parameter(view, fix)
    template_id = view.ViewTemplateId
    if parameter is None or template_id == DB.ElementId.InvalidElementId:
        return view
    template = view.Document.GetElement(template_id)
    if template is None:
        return view
    controlled = id_value(DB.ElementId(parameter))
    non_controlled = set(
        id_value(pid) for pid in template.GetNonControlledTemplateParameterIds()
    )
    return view if controlled in non_controlled else template


def describe(view, fix):
    """Return the UI description of a fix in the context of ``view``.

    Returns:
        (dict): ``label`` for the button, ``template`` (name or None) when the
        fix edits the view template, and ``navigation`` when the action only
        changes what Revit shows and does not modify the model.
    """
    key, default = _LABELS.get(fix.get("action"), ("", fix.get("action")))
    label = t(key, default) if key else default
    owner = settings_owner(view, fix)
    template_name = owner.Name if owner.Id != view.Id else None
    if template_name:
        label = t("fix_in_template", "{} (in template '{}')").format(
            label, template_name
        )
    return {
        "label": label,
        "template": template_name,
        "navigation": fix.get("action") in NAVIGATION_ACTIONS,
    }


def _show_workset(owner, view, element, fix):
    owner.SetWorksetVisibility(
        DB.WorksetId(int(fix["workset_id"])), DB.WorksetVisibility.Visible
    )


def _unhide_category(owner, view, element, fix):
    category_id = _element_id(fix["category_id"])
    if not owner.CanCategoryBeHidden(category_id):
        raise FixError(
            t(
                "fix_error_category_locked",
                "This category's visibility cannot be changed in this view",
            )
        )
    owner.SetCategoryHidden(category_id, False)


def _unhide_element(owner, view, element, fix):
    view.UnhideElements(List[DB.ElementId]([element.Id]))


def _reset_temporary_hide(owner, view, element, fix):
    view.DisableTemporaryViewMode(DB.TemporaryViewMode.TemporaryHideIsolate)


def _show_filter(owner, view, element, fix):
    owner.SetFilterVisibility(_element_id(fix["filter_id"]), True)


def _expand_section_box(owner, view, element, fix):
    bbox = element.get_BoundingBox(None)
    box = view.GetSectionBox()
    if bbox is None or box is None:
        raise FixError(
            t("fix_error_no_extents", "The element has no extents to include")
        )
    low, high = local_extents(box.Transform, bbox)
    expanded = DB.BoundingBoxXYZ()
    expanded.Transform = box.Transform
    expanded.Min = DB.XYZ(
        min(box.Min.X, low.X - _MARGIN_FT),
        min(box.Min.Y, low.Y - _MARGIN_FT),
        min(box.Min.Z, low.Z - _MARGIN_FT),
    )
    expanded.Max = DB.XYZ(
        max(box.Max.X, high.X + _MARGIN_FT),
        max(box.Max.Y, high.Y + _MARGIN_FT),
        max(box.Max.Z, high.Z + _MARGIN_FT),
    )
    view.SetSectionBox(expanded)


def _disable_crop(owner, view, element, fix):
    view.CropBoxActive = False


def _disable_far_clip(owner, view, element, fix):
    owner.get_Parameter(DB.BuiltInParameter.VIEWER_BOUND_FAR_CLIPPING).Set(0)


def _extend_view_range(owner, view, element, fix):
    """Move one view range plane just past the element.

    Floor plans: "up" raises the top clip plane, "down" lowers view depth.
    Ceiling plans: "up" raises view depth, which may sit above the top plane.
    The plane keeps its associated level; only the offset changes.

    Invariant:
        Planes only move outward. "Fix all" applies this once per element,
        and a lower element processed later must not pull the plane back
        past an element handled earlier.
    """
    bbox = element.get_BoundingBox(None)
    if bbox is None:
        raise FixError(
            t("fix_error_no_extents", "The element has no extents to include")
        )
    doc = view.Document
    is_rcp = view.ViewType == DB.ViewType.CeilingPlan
    view_range = owner.GetViewRange()
    if fix.get("direction") == "up":
        plane = (
            DB.PlanViewPlane.ViewDepthPlane if is_rcp else DB.PlanViewPlane.TopClipPlane
        )
        target = bbox.Max.Z + _MARGIN_FT
    else:
        plane = DB.PlanViewPlane.ViewDepthPlane
        target = bbox.Min.Z - _MARGIN_FT
    current = resolve_view_range_elevation(doc, view_range, plane)
    if current is not None and (
        current >= target if fix.get("direction") == "up" else current <= target
    ):
        return
    level = doc.GetElement(view_range.GetLevelId(plane))
    if level is None:
        raise FixError(
            t(
                "fix_error_unlimited_plane",
                "The view range plane is not tied to a level",
            )
        )
    view_range.SetOffset(plane, target - level.Elevation)
    owner.SetViewRange(view_range)
    lower, upper = get_view_range_bounds(doc, view)
    if (fix.get("direction") == "up" and upper is not None and upper < target) or (
        fix.get("direction") != "up" and lower is not None and lower > target
    ):
        raise FixError(
            t("fix_error_view_range", "Revit rejected the extended view range")
        )


def _raise_cut_plane(owner, view, element, fix):
    """Move the cut plane just above the element so it draws in projection.

    For cuttable elements entirely between the cut plane and the top, which
    plan views do not draw. Putting the cut above the element makes it an
    element below the cut plane, drawn with its projection line weight. The
    top clip plane is raised too when it would end up below the new cut,
    since Revit requires top >= cut. Planes keep their associated levels.
    The cut only moves up, for the same reason as in ``_extend_view_range``.

    Warning:
        This changes how everything else in the view is cut (e.g. walls are
        now cut higher). A plan region is the local alternative, but plan
        regions cannot be created through the API.
    """
    bbox = element.get_BoundingBox(None)
    if bbox is None:
        raise FixError(
            t("fix_error_no_extents", "The element has no extents to include")
        )
    doc = view.Document
    view_range = owner.GetViewRange()
    target = bbox.Max.Z + _MARGIN_FT
    current_cut = resolve_view_range_elevation(
        doc, view_range, DB.PlanViewPlane.CutPlane
    )
    if current_cut is not None and current_cut >= target:
        return
    cut_level = doc.GetElement(view_range.GetLevelId(DB.PlanViewPlane.CutPlane))
    if cut_level is None:
        raise FixError(
            t(
                "fix_error_unlimited_plane",
                "The view range plane is not tied to a level",
            )
        )
    top = resolve_view_range_elevation(doc, view_range, DB.PlanViewPlane.TopClipPlane)
    if top is not None and top < target + _MARGIN_FT:
        top_level = doc.GetElement(view_range.GetLevelId(DB.PlanViewPlane.TopClipPlane))
        view_range.SetOffset(
            DB.PlanViewPlane.TopClipPlane,
            target + _MARGIN_FT - top_level.Elevation,
        )
    view_range.SetOffset(DB.PlanViewPlane.CutPlane, target - cut_level.Elevation)
    owner.SetViewRange(view_range)
    cut = resolve_view_range_elevation(
        doc, view.GetViewRange(), DB.PlanViewPlane.CutPlane
    )
    if cut is None or cut < bbox.Max.Z:
        raise FixError(
            t("fix_error_view_range", "Revit rejected the extended view range")
        )


def _set_discipline_coordination(owner, view, element, fix):
    owner.get_Parameter(DB.BuiltInParameter.VIEW_DISCIPLINE).Set(
        int(DB.ViewDiscipline.Coordination)
    )


_MODEL_ACTIONS = {
    "show_workset": _show_workset,
    "unhide_category": _unhide_category,
    "unhide_element": _unhide_element,
    "reset_temporary_hide": _reset_temporary_hide,
    "show_filter": _show_filter,
    "expand_section_box": _expand_section_box,
    "disable_crop": _disable_crop,
    "disable_far_clip": _disable_far_clip,
    "extend_view_range": _extend_view_range,
    "raise_cut_plane": _raise_cut_plane,
    "set_discipline_coordination": _set_discipline_coordination,
}


def open_view(uidoc, view):
    """Ask Revit to activate ``view``; Revit switches once the call returns."""
    uidoc.RequestViewChange(view)


def apply(uidoc, view, element, fix):
    """Apply a fix descriptor to ``view`` for ``element``.

    Navigation actions only change the active view. Model actions run in one
    transaction named after the fix label.

    Raises:
        FixError: the action is unknown, its target vanished, or Revit
            rejected the change. Every other exception, including those from
            resolving the descriptor, is wrapped, so callers only handle this.
    """
    action = fix.get("action")
    doc = view.Document
    try:
        if action == "open_view":
            target = doc.GetElement(_element_id(fix["view_id"]))
            if target is None:
                raise FixError(t("fix_error_missing", "The target no longer exists"))
            open_view(uidoc, target)
            return
        handler = _MODEL_ACTIONS.get(action)
        if handler is None:
            raise FixError("Unknown action '{}'".format(action))
        owner = settings_owner(view, fix)
        label = describe(view, fix)["label"]
    except FixError:
        raise
    except Exception as ex:
        raise FixError(str(ex))
    transaction = DB.Transaction(
        doc, "{}: {}".format(t("report_title", "Visibility Diagnosis"), label)
    )
    transaction.Start()
    try:
        handler(owner, view, element, fix)
    except FixError:
        transaction.RollBack()
        raise
    except Exception as ex:
        transaction.RollBack()
        raise FixError(str(ex))
    status = transaction.Commit()
    if status != DB.TransactionStatus.Committed:
        raise FixError(
            t("fix_error_rolled_back", "Revit rolled the change back ({})").format(
                status
            )
        )
