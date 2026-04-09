# -*- coding: utf-8 -*-
from pyrevit import revit, script

from match.match_utils import paste_props, PropKeyValue, safe_get_parameter
from match.filter_utils import (
    get_color_source_parameter,
    get_most_common_ogs_brush,
    get_contrasting_brush,
)

logger = script.get_logger()


def main():
    sel = revit.get_selection()
    elem = sel[0] if len(sel) == 1 else revit.pick_element(message="Pick Element to gather Parameter Value")
    if not elem:
        return
    param_id, ogs = get_color_source_parameter(revit.doc, revit.active_view, elem)
    if not param_id:
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

    bg = get_most_common_ogs_brush(ogs)
    fg = get_contrasting_brush(bg)

    paste_props(props, "single", background=bg, foreground=fg)


if __name__ == "__main__":
    main()
