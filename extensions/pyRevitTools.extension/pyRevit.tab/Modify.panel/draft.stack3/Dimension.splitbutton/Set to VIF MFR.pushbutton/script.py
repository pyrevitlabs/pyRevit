"""Sets dimension value to VERIFY W MFR on selected dimensions."""

from pyrevit import revit, DB


with revit.Transaction('VWM dimensions'):
    for elId in revit.uidoc.Selection.GetElementIds():
        el = revit.doc.GetElement(elId)
        if isinstance(el, DB.Dimension):
            if len(list(el.Segments)) > 0:
                for seg in el.Segments:
                    seg.Suffix = 'R.O.'
                    seg.Below = 'VERIFY W/ MFR'
            else:
                el.Suffix = 'R.O.'
                el.Below = 'VERIFY W/ MFR'
