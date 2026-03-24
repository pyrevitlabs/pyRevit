# -*- coding: utf-8 -*-
from pyrevit import revit, script

from match.match_utils import paste_props, PropKeyValue, safe_get_parameter
from match.filter_utils import get_most_common_filter_parameter

logger = script.get_logger()


def main():
    param_id = get_most_common_filter_parameter(revit.doc, revit.active_view)
    if not param_id:
        return
    sel = revit.get_selection()
    elem = sel[0] if len(sel) == 1 else revit.pick_element()
    if not elem:
        return
    props = []
    try:
        tparam = safe_get_parameter(elem, param_id)
        if not tparam:
            return
        value = revit.query.get_param_value(tparam)
        props = [
            PropKeyValue(
                name=tparam.Definition.Name,
                datatype=tparam.StorageType,
                value=value,
                istype=False,
                display_value=tparam.AsValueString() or str(value),
                categories=[elem.Category],
            )
        ]
    except Exception as ex:
        logger.warning("load_from_filter_and_element: %s", ex)
        return

    if not props:
        return

    paste_props(props, "single")


if __name__ == "__main__":
    main()
