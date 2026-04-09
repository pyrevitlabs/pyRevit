# -*- coding: utf-8 -*-
from pyrevit import script, forms, revit
from pyrevit import DB, UI
from pyrevit.compat import get_elementid_value_func

get_elementid_value = get_elementid_value_func()

logger = script.get_logger()


def safe_get_parameter(elem, param_id):
    if not param_id:
        return None

    try:
        pid_val = get_elementid_value(param_id)

        # BuiltInParameter (negative ids)
        if pid_val < 0:
            bip = DB.BuiltInParameter(pid_val)
            return elem.get_Parameter(bip)

        # Shared / Project Parameter
        doc = elem.Document
        param_el = doc.GetElement(param_id)

        if not param_el:
            return None

        # Prefer GUID
        if hasattr(param_el, "GuidValue"):
            guid = param_el.GuidValue
            if guid:
                return elem.get_Parameter(guid)

        # Fallback - this should not be entered, as this would mean a non-filterable parameter
        definition = (
            param_el.GetDefinition() if hasattr(param_el, "GetDefinition") else None
        )
        if definition:
            return param_el.get_Parameter(definition)

    except Exception:
        return None


class PickByCategorySelectionFilter(UI.Selection.ISelectionFilter):
    def __init__(self, category_ids):
        self.category_ids = category_ids

    # standard API override function
    def AllowElement(self, element):
        if element.Category and element.Category.Id in self.category_ids:
            return True
        else:
            return False

    # standard API override function
    def AllowReference(self, refer, point):  # pylint: disable=W0613
        return False


class PropKeyValue(object):
    """Storage class for matched property info and value."""

    def __init__(
        self, name, datatype, value, istype, display_value=None, categories=None
    ):
        self.name = name
        self.datatype = datatype
        self.value = value
        self.istype = istype
        self.display_value = display_value or name
        self.categories = categories if categories is not None else []

    def __repr__(self):
        return str(self.__dict__)


def match_prop(dest_inst, dest_type, src_props):
    """Match given properties on target instance or type"""
    for pkv in src_props:
        logger.debug("Applying %s", pkv.name)

        # determine target
        target = dest_type if pkv.istype else dest_inst
        # ensure target is valid if it is type
        if pkv.istype and not target:
            logger.warning("Element type is not accessible.")
            continue
        logger.debug("Target is %s", target)

        # find parameter
        dparam = target.LookupParameter(pkv.name)
        if dparam and pkv.datatype == dparam.StorageType:
            try:
                if dparam.StorageType == DB.StorageType.Integer:
                    dparam.Set(pkv.value or 0)
                elif dparam.StorageType == DB.StorageType.Double:
                    dparam.Set(pkv.value or 0.0)
                elif dparam.StorageType == DB.StorageType.ElementId:
                    if not isinstance(pkv.value, DB.ElementId):
                        dparam.Set(DB.ElementId(pkv.value))
                    else:
                        dparam.Set(pkv.value)
                else:
                    dparam.Set(pkv.value or "")
            except Exception as setex:
                logger.warning("Error applying value to: %s | %s", pkv.name, setex)
                continue
        else:
            logger.debug('Parameter "%s"not found on target.', pkv.name)


def get_source_properties(src_element, simple=False):
    """Return info on selected properties."""
    props = []

    src_type = revit.query.get_type(src_element)

    selected_params = (
        forms.select_parameters(
            src_element,
            title="Select Parameters",
            multiple=True,
            include_instance=True,
            include_type=True,
        )
        or []
    )

    logger.debug("Selected parameters: %s", [x.name for x in selected_params])

    for sparam in selected_params:
        logger.debug("Reading %s", sparam.name)
        target = src_type if sparam.istype else src_element
        tparam = target.LookupParameter(sparam.name)
        if tparam:
            if tparam.StorageType == DB.StorageType.Integer:
                value = tparam.AsInteger()
            elif tparam.StorageType == DB.StorageType.Double:
                value = tparam.AsDouble()
            elif tparam.StorageType == DB.StorageType.ElementId:
                value = get_elementid_value(tparam.AsElementId())
            else:
                value = tparam.AsString()

            props.append(
                PropKeyValue(
                    name=sparam.name,
                    datatype=tparam.StorageType,
                    value=value,
                    istype=sparam.istype,
                    display_value=tparam.AsValueString() if not simple else None,
                    categories=[src_element.Category] if not simple else [],
                )
            )

    return props


def paste_props(source_props, paste_mode, category_filter=False, **kwargs):
    """
    paste_mode: "single" | "rectangle" | "selection"
    """
    # Build category filter if the checkbox is ticked and categories are known
    pick_filter = None
    if category_filter:
        cat_ids = set()
        for p in source_props:
            for c in p.categories or []:
                if hasattr(c, "Id"):
                    cat_ids.add(c.Id)
        if cat_ids:
            pick_filter = PickByCategorySelectionFilter(list(cat_ids))

    # Status-bar message shown to the user while picking
    if len(source_props) == 1:
        title = "Match: {} = {}".format(
            source_props[0].name,
            source_props[0].display_value or str(source_props[0].value),
        )
    else:
        title = "Pick elements to match {} parameter(s):".format(len(source_props))

    bg = kwargs.get("background", None)
    fg = kwargs.get("foreground", None)
    with forms.WarningBar(title=title, background=bg, foreground=fg):
        while True:
            dest_elements = []

            if paste_mode == "single":
                elem = revit.pick_element(pick_filter=pick_filter)
                if elem:
                    dest_elements = [elem]

            elif paste_mode == "rectangle":
                try:
                    dest_elements = revit.pick_rectangle(pick_filter=pick_filter)
                except Exception:
                    # To handle esc by user, this would throw a OperationCanceledException
                    pass

            elif paste_mode == "selection":
                dest_elements = list(revit.get_selection())
                if category_filter:
                    dest_elements = [
                        el for el in dest_elements
                        if el.Category and el.Category.Id in cat_ids
                    ]

            if not dest_elements:
                break  # user cancelled / nothing selected

            for dest in dest_elements:
                dest_type = revit.query.get_type(dest)
                with revit.Transaction("Match Properties"):
                    # type parameters first so instance params can reference them
                    match_prop(dest, dest_type, [p for p in source_props if p.istype])
                    match_prop(
                        dest, dest_type, [p for p in source_props if not p.istype]
                    )

            if paste_mode == "selection":
                break  # selection is one-shot, not a pick loop
