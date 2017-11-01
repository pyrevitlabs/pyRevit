from pyrevit import revit, DB


__doc__ = 'Sets element graphic override to halftone on the selected '\
           'elements. If any of the elements is a group, '\
           'the script will apply the override to all its members.'


selection = revit.get_selection()

with revit.Transaction('Halftone Elements in View'):
    for el in selection:
        if isinstance(el, DB.Group):
            for mem in el.GetMemberIds():
                selection.append(revit.doc.GetElement(mem))
        ogs = DB.OverrideGraphicSettings()
        ogs.SetHalftone(True)
        # ogs.SetProjectionFillPatternVisible(False)
        revit.doc.ActiveView.SetElementOverrides(el.Id, ogs)
