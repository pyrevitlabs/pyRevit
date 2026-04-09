# -*- coding: utf-8 -*-
from collections import Counter

from pyrevit.revit import query
from pyrevit import DB
from pyrevit.framework import SolidColorBrush, Color
from pyrevit.compat import get_elementid_value_func

get_elementid_value = get_elementid_value_func()


def dissect_parameter_filter(doc, filter_element):
    """
    Extract information from a simple equals ParameterFilterElement.

    Returns a dict, or None if the filter is not a single equals rule.

    Keys:
        parameter_id   – DB.ElementId of the parameter
        parameter_name – human-readable name string
        categories     – list of categories
        storage_type   – DB.StorageType enum value
        value          – raw value (int / float / str / get_elementid_value(DB.ElementId))
        display_value  – formatted string for display
        rule           – the raw Revit filter rule object
    """

    result = {
        "parameter_id": None,
        "parameter_name": None,
        "categories": [],
        "storage_type": None,
        "value": None,
        "display_value": None,
        "rule": None,
    }

    # ── categories ────────────────────────────────────────────────────
    try:
        for cid in filter_element.GetCategories():
            bic = DB.BuiltInCategory(get_elementid_value(cid))
            cat = doc.Settings.Categories.get_Item(bic)
            if cat:
                result["categories"].append(cat)
    except Exception:
        pass

    # ── unwrap to ElementParameterFilter ─────────────────────────────
    element_filter = filter_element.GetElementFilter()

    if isinstance(element_filter, (DB.LogicalAndFilter, DB.LogicalOrFilter)):
        sub_filters = element_filter.GetFilters()
        if len(sub_filters) != 1:
            return None
        element_filter = sub_filters[0]

    if not isinstance(element_filter, DB.ElementParameterFilter):
        return None

    rules = element_filter.GetRules()
    if len(rules) != 1:
        return None

    rule = rules[0]

    # ── unwrap inverted rules ─────────────────────────────────────────
    if isinstance(rule, DB.FilterInverseRule):
        return None

    # extra safeguard (future-proof)
    if not hasattr(rule, "GetRuleParameter") or not hasattr(rule, "GetEvaluator"):
        return None

    result["rule"] = rule

    # ── parameter id / name ───────────────────────────────────────────
    param_id = rule.GetRuleParameter()
    result["parameter_id"] = param_id

    param_elem = doc.GetElement(param_id)
    if param_elem:
        result["parameter_name"] = param_elem.Name
    else:
        try:
            bip = DB.BuiltInParameter(get_elementid_value(param_id))
            result["parameter_name"] = DB.LabelUtils.GetLabelFor(bip)
        except Exception:
            result["parameter_name"] = str(get_elementid_value(param_id))

    # ── evaluator must be equals ──────────────────────────────────────
    evaluator = rule.GetEvaluator()
    if not isinstance(evaluator, (DB.FilterNumericEquals, DB.FilterStringEquals)):
        return None

    # ── value extraction (sets storage_type as DB.StorageType enum) ───
    if isinstance(rule, DB.FilterStringRule):
        val = rule.RuleString
        result["storage_type"] = DB.StorageType.String
        result["value"] = val
        result["display_value"] = val

    elif isinstance(rule, DB.FilterDoubleRule):
        val = rule.RuleValue
        result["storage_type"] = DB.StorageType.Double
        result["value"] = val
        try:
            spec = None
            if param_elem:
                spec = param_elem.GetDataType()
            else:
                try:
                    bip = DB.BuiltInParameter(get_elementid_value(param_id))
                    bics = [query.get_builtincategory(bic_name) for bic_name in result["categories"]]
                    collector = query.get_elements_by_categories(bics)
                    elem = next(iter(collector), None)
                    param = elem.get_Parameter(bip) if elem else None
                    if param:
                        spec = param.Definition.GetDataType()
                except Exception:
                    pass
            display = DB.UnitFormatUtils.Format(
                doc.GetUnits(), spec, val, False
            )
        except Exception:
            display = str(val)
        result["display_value"] = display

    elif isinstance(rule, DB.FilterIntegerRule):
        val = rule.RuleValue
        result["storage_type"] = DB.StorageType.Integer
        result["value"] = val
        # special case: workset parameter
        if get_elementid_value(param_id) == int(
            DB.BuiltInParameter.ELEM_PARTITION_PARAM
        ):
            try:
                ws = doc.GetWorksetTable().GetWorkset(DB.WorksetId(val))
                result["display_value"] = ws.Name if ws else str(val)
            except Exception:
                result["display_value"] = str(val)
        else:
            result["display_value"] = str(val)

    elif isinstance(rule, DB.FilterElementIdRule):
        val = rule.RuleValue
        result["storage_type"] = DB.StorageType.ElementId
        result["value"] = get_elementid_value(val)
        elem = doc.GetElement(val)
        if elem:
            try:
                result["display_value"] = elem.Name
            except Exception:
                result["display_value"] = str(get_elementid_value(val))
        else:
            result["display_value"] = str(get_elementid_value(val))

    else:
        return None

    return result


def get_most_common_filter_parameter(doc, view):
    """
    Return the ElementId of the parameter used most often in simple
    equals filters on the given view.  Returns None if none found.
    """
    param_count = {}

    filters = query.get_view_filters(view)
    for f in filters:
        if not isinstance(f, DB.ParameterFilterElement):
            continue
        info = dissect_parameter_filter(doc, f)
        if not info:
            continue
        pid = info["parameter_id"]
        param_count[pid] = param_count.get(pid, 0) + 1

    if not param_count:
        return None

    return max(param_count, key=param_count.get)


def get_color_source_parameter(doc, view, element=None):
    """
    Determine the parameter responsible for color in the view.

    Priority:
    1. Element overrides (if element is given)
    2. First matching filter with overrides

    Returns:
        ElementId of the parameter, the filters OverrideGraphicSettings or None, None
    """

    # --------------------------------------------------
    # 1. ELEMENT OVERRIDES (highest priority)
    # --------------------------------------------------
    if element:
        try:
            ogs = view.GetElementOverrides(element.Id)
            if ogs and ogs_has_overrides(ogs):
                return None, ogs
        except Exception:
            pass

    # --------------------------------------------------
    # 2. FILTER ANALYSIS
    # --------------------------------------------------
    filters = query.get_view_filters(view)

    for f in filters:
        try:
            if not isinstance(f, DB.ParameterFilterElement):
                continue

            if not view.GetIsFilterEnabled(f.Id):
                continue

            if element:
                element_filter = f.GetElementFilter()
                if element_filter is None or not element_filter.PassesFilter(element):
                    continue

            ogs = view.GetFilterOverrides(f.Id)
            if not ogs_has_overrides(ogs):
                continue

            info = dissect_parameter_filter(doc, f)
            if not info:
                continue

            return info["parameter_id"], ogs

        except Exception:
            continue

    return None, None


def ogs_has_overrides(ogs):
    """Return True if OverrideGraphicSettings has any overrides set."""

    if ogs is None:
        return False

    invalid_id = DB.ElementId.InvalidElementId

    checks = [
        # Line weights
        ogs.ProjectionLineWeight != -1,
        ogs.CutLineWeight != -1,
        # Line colors
        ogs.ProjectionLineColor.IsValid,
        ogs.CutLineColor.IsValid,
        # Line patterns
        ogs.ProjectionLinePatternId != invalid_id,
        ogs.CutLinePatternId != invalid_id,
        # Fill patterns
        ogs.SurfaceForegroundPatternId != invalid_id,
        ogs.SurfaceBackgroundPatternId != invalid_id,
        ogs.CutForegroundPatternId != invalid_id,
        ogs.CutBackgroundPatternId != invalid_id,
        # Fill colors
        ogs.SurfaceForegroundPatternColor.IsValid,
        ogs.SurfaceBackgroundPatternColor.IsValid,
        ogs.CutForegroundPatternColor.IsValid,
        ogs.CutBackgroundPatternColor.IsValid,
        # Transparency
        ogs.Transparency != 0,
        # Halftone
        ogs.Halftone,
        # Detail level
        ogs.DetailLevel != DB.ViewDetailLevel.Undefined,
        # Visibility
        ogs.IsSurfaceForegroundPatternVisible == False,  # noqa: E712
        ogs.IsSurfaceBackgroundPatternVisible == False,  # noqa: E712
        ogs.IsCutForegroundPatternVisible == False,  # noqa: E712
        ogs.IsCutBackgroundPatternVisible == False,  # noqa: E712
    ]

    return any(checks)


def get_most_common_ogs_brush(ogs):
    """
    Given a OverrideGraphicSettings, return the most common color
    as a WPF SolidColorBrush.
    """

    if not ogs:
        return None

    colors = []

    def add_color(c):
        if c and c.IsValid:
            colors.append((c.Red, c.Green, c.Blue))

    # Collect all possible color overrides
    add_color(ogs.ProjectionLineColor)
    add_color(ogs.CutLineColor)

    add_color(ogs.SurfaceForegroundPatternColor)
    add_color(ogs.SurfaceBackgroundPatternColor)

    add_color(ogs.CutForegroundPatternColor)
    add_color(ogs.CutBackgroundPatternColor)

    if not colors:
        return None

    # Find most common RGB tuple
    most_common_rgb, _ = Counter(colors).most_common(1)[0]

    r, g, b = most_common_rgb

    # Convert to WPF SolidColorBrush (ARGB, Alpha=255)
    media_color = Color.FromArgb(255, r, g, b)
    return SolidColorBrush(media_color)


def get_contrasting_brush(accent_brush):
    """
    Given a SolidColorBrush, return a high-contrast SolidColorBrush (black/white).
    """

    if not accent_brush:
        return SolidColorBrush(Color.FromArgb(255, 0, 0, 0))  # fallback black

    c = accent_brush.Color

    # Perceived luminance (standard formula)
    luminance = 0.299 * c.R + 0.587 * c.G + 0.114 * c.B

    # Threshold ~128 works well
    if luminance > 128:
        # bright background → dark text
        return SolidColorBrush(Color.FromArgb(255, 0, 0, 0))
    else:
        # dark background → light text
        return SolidColorBrush(Color.FromArgb(255, 255, 255, 255))


def get_ogs_from_prop_in_view(doc, view, prop):
    """
    Given a PropKeyValue and a view, find the first matching
    ParameterFilterElement and return its OverrideGraphicSettings.

    Returns:
        OverrideGraphicSettings or None
    """

    filters = query.get_view_filters(view)

    for f in filters:
        try:
            if not isinstance(f, DB.ParameterFilterElement):
                continue

            if not view.GetIsFilterEnabled(f.Id):
                continue

            info = dissect_parameter_filter(doc, f)
            if not info:
                continue

            # --------------------------------------------------
            # MATCH LOGIC
            # --------------------------------------------------

            # 1. Parameter name must match
            if info["parameter_name"] != prop.name:
                continue

            # 2. Storage type must match
            if info["storage_type"] != prop.datatype:
                continue

            # 3. Value must match
            # (important: use raw value, not display string)
            if info["value"] != prop.value:
                continue

            # 4. Optional: category match (safer)
            if prop.categories:
                prop_cat_ids = set(
                    get_elementid_value(c.Id)
                    for c in prop.categories
                    if c
                )
                filter_cat_ids = set(
                    get_elementid_value(cat_id)
                    for cat_id in (f.GetCategories() or [])
                    if cat_id
                )
                if filter_cat_ids and not prop_cat_ids.intersection(filter_cat_ids):
                    continue

            # --------------------------------------------------
            # OGS
            # --------------------------------------------------
            ogs = view.GetFilterOverrides(f.Id)
            if not ogs_has_overrides(ogs):
                continue

            return ogs

        except Exception:
            continue

    return None
