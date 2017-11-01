from pyrevit import revit, DB


__doc__ = 'Sets the element graphic overrides to '\
          'white projection color on the selected elements.'


selection = revit.get_selection()

with revit.Transaction('Whiteout Selected Elements'):
    for el in selection:
        if isinstance(el, DB.Group):
            for mem in el.GetMemberIds():
                selection.append(revit.doc.GetElement(mem))
        ogs = DB.OverrideGraphicSettings()
        ogs.SetProjectionLineColor(DB.Color(255, 255, 255))
        revit.doc.ActiveView.SetElementOverrides(el.Id, ogs)
