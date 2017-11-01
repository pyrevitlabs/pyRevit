from pyrevit import revit, DB


__doc__ = 'Add special non-printable character to existing '\
          'dimension value of selected dimensions and adds.'


with revit.Transaction('Overrride dims value'):
    for elId in revit.uidoc.Selection.GetElementIds():
        el = revit.doc.GetElement(elId)
        if isinstance(el, DB.Dimension):
            if len(list(el.Segments)) > 0:
                for seg in el.Segments:
                    exitingValue = seg.ValueString
                    seg.ValueOverride = u'\u200e' + exitingValue
            else:
                exitingValue = el.ValueString
                el.ValueOverride = u'\u200e' + exitingValue
