from pyrevit import revit, DB


__context__ = 'selection'
__doc__ = 'Brings selected object to Front of the current view. '\
          'This only works on elements that support this option.'


with revit.Transaction('Bring Selected To Front'):
    for elId in revit.uidoc.Selection.GetElementIds():
        try:
            DB.DetailElementOrderUtils.BringForward(revit.doc,
                                                    revit.activeview,
                                                    elId)
        except Exception:
            continue
