from pyrevit import revit, DB


__doc__ = 'Sets the element graphic override to Solid projection '\
          'lines for the selected elements.'


selection = revit.get_selection()

with revit.Transaction("Set Element to Solid Projection Line Pattern"):
    for el in selection:
        if el.ViewSpecific:
            ogs = DB.OverrideGraphicSettings()
            ogs.SetProjectionLinePatternId(
                DB.LinePatternElement.GetSolidPatternId()
                )
            revit.doc.ActiveView.SetElementOverrides(el.Id, ogs)
