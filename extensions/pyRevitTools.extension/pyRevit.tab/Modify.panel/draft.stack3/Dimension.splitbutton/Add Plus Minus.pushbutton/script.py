"""Adds +- prefix to selected dimensions."""

from pyrevit import revit, DB

with revit.Transaction('add plusMinus to dims'):
    for elId in revit.uidoc.Selection.GetElementIds():
        el = revit.doc.GetElement(elId)
        if isinstance(el, DB.Dimension):
            if len(list(el.Segments)) > 0:
                for seg in el.Segments:
                    seg.Prefix = u'\xb1'
            else:
                el.Prefix = u'\xb1'
