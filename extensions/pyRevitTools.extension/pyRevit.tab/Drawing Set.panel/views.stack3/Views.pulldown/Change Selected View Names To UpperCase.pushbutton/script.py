"""Changes the selected view names to UPPERCASE."""

from pyrevit import revit, DB


with revit.Transaction('Batch Rename Views'):
    for el_id in revit.get_selection().element_ids:
        el = revit.doc.GetElement(el_id)
        if isinstance(el, DB.Viewport):
            el = revit.doc.GetElement(el.ViewId)
        name = el.ViewName
        el.ViewName = el.ViewName.upper()
        print("VIEW: {0}\n"
              "\tRENAMED TO:\n"
              "\t{1}\n\n".format(name, el.ViewName))
