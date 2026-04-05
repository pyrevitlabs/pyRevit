# -*- coding: utf-8 -*-
from pyrevit.revit import query
from pyrevit import DB
from pyrevit.compat import get_elementid_value_func

get_elementid_value = get_elementid_value_func()


def dissect_parameter_filter(doc, filter_element):
    """
    Extract information from a simple equals ParameterFilterElement.

    Returns a dict, or None if the filter is not a single equals rule.

    Keys:
        parameter_id   – DB.ElementId of the parameter
        parameter_name – human-readable name string
        categories     – list of category name strings
        storage_type   – DB.StorageType enum value
        value          – raw value (int / float / str / DB.ElementId)
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
                result["categories"].append(cat.Name)
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
        result["value"] = val
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

    for fid in view.GetFilters():
        filter_elem = doc.GetElement(fid)
        if not isinstance(filter_elem, DB.ParameterFilterElement):
            continue
        info = dissect_parameter_filter(doc, filter_elem)
        if not info:
            continue
        pid = info["parameter_id"]
        param_count[pid] = param_count.get(pid, 0) + 1

    if not param_count:
        return None

    return max(param_count, key=param_count.get)
