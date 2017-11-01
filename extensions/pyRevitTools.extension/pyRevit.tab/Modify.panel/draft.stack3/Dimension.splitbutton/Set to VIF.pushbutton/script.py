"""Sets dimension value to VERIFY IN FIELD on selected dimensions."""

from pyrevit import revit, DB

with revit.Transaction('VIF dimensions'):
    for elId in revit.uidoc.Selection.GetElementIds():
        el = revit.doc.GetElement(elId)
        if isinstance(el, DB.Dimension):
            if len(list(el.Segments)) > 0:
                for seg in el.Segments:
                    seg.Below = 'VIF'
            else:
                el.Below = 'VIF'
