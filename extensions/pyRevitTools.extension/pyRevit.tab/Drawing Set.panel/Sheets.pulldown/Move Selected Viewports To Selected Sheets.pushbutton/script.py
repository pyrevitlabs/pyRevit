from pyrevit import revit, DB, UI


__doc__ = 'Open interfacetypes sheet. Select ONE other sheet in '\
          'Project Browser. Run this script (Keep focus on Project Browser '\
          'otherwise the current selection will not show the selected '\
          'sheets). Select Viewports and push Finish button on the '\
          'properties bar. The selected views will be MOVED to '\
          'the selected sheet.'


selection = revit.get_selection()

selSheets = []
selViewports = []

for el in selection:
    if isinstance(el, UI.ViewSheet):
        selSheets.append(el)

if 0 < len(selSheets) <= 2:
    if int(__revit__.Application.VersionNumber) > 2014:
        cursheet = revit.activeview
        for v in selSheets:
            if cursheet.Id == v.Id:
                selSheets.remove(v)
    else:
        cursheet = selSheets[0]
        selSheets.remove(cursheet)

    revit.activeview = cursheet
    sel = revit.uidoc.Selection.PickObjects(UI.Selection.ObjectType.Element)
    for el in sel:
        selViewports.append(revit.doc.GetElement(el))

    if len(selViewports) > 0:
        with revit.Transaction('Move Viewports'):
            for sht in selSheets:
                for vp in selViewports:
                    if isinstance(vp, UI.Viewport):
                        viewId = vp.ViewId
                        vpCenter = vp.GetBoxCenter()
                        vpTypeId = vp.GetTypeId()
                        cursheet.DeleteViewport(vp)
                        nvp = UI.Viewport.Create(revit.doc,
                                                 sht.Id,
                                                 viewId,
                                                 vpCenter)
                        nvp.ChangeTypeId(vpTypeId)
                    elif isinstance(vp, UI.ScheduleSheetInstance):
                        nvp = \
                            UI.ScheduleSheetInstance.Create(
                                revit.doc, sht.Id, vp.ScheduleId, vp.Point
                                )
                        revit.doc.Delete(vp.Id)
    else:
        UI.TaskDialog.Show('pyrevit',
                           'At least one viewport must be selected.')
elif len(selSheets) == 0:
    UI.TaskDialog.Show('pyrevit',
                       'You must select at least one sheet to add '
                       'the selected viewports to.')
elif len(selSheets) > 2:
    UI.TaskDialog.Show('pyrevit',
                       'Maximum of two sheets can only be selected.')
