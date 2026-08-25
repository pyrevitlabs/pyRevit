# -*- coding: utf-8 -*-
from pyrevit import revit, script
from pyrevit import DB
from pyrevit.compat import get_elementid_value_func

from match.match_utils import paste_props, PropKeyValue
from match.filter_utils import (
    get_color_source_parameter,
    get_most_common_ogs_brush,
    get_contrasting_brush,
)

get_elementid_value = get_elementid_value_func()
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
        tparam = revit.query.get_param(elem, param_id)
        if not tparam:
            return
        value = revit.query.get_param_value(tparam)
        props = [
            PropKeyValue(
                name=tparam.Definition.Name,
                datatype=tparam.StorageType,
                value=get_elementid_value(value) if isinstance(value, DB.ElementId) else value,
                istype=False,
                display_value=tparam.AsValueString() or str(value),
                categories=[elem.Category],
            )
        ]
    except Exception as ex:
        logger.error("Cancelling match value picker: %s", ex)
        return

    if not props:
        return

    bg = get_most_common_ogs_brush(ogs)
    fg = get_contrasting_brush(bg)

    paste_props(props, "single", background=bg, foreground=fg)


if __name__ == "__main__":
    main()
