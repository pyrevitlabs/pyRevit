from pyrevit import revit, DB, UI


__title__ = 'Copy/Update Selected Viewports To Selected Sheets'

__doc__ = 'Open the source sheet. Select other sheets in Project Browser. '\
          'Run this script (Keep focus on Project Browser otherwise the ' \
          'current selection will not show the selected sheets). ' \
          'Select Viewports and push Finish button on the properties bar. ' \
          'The selected views will be added to the selected sheets. ' \
          'If the view or schedule already exists on that sheet, the ' \
          'location and viewport type will be updated.'


selSheets = []
selViewports = []
selection = revit.get_selection()
allSheetedSchedules = DB.FilteredElementCollector(revit.doc)\
                        .OfClass(DB.ScheduleSheetInstance)\
                        .ToElements()


# cleanup list of selected sheets
for el in selection:
    if isinstance(el, DB.ViewSheet):
        selSheets.append(el)

# get a list of viewports to be copied, updated
if len(selSheets) > 0:
    if int(__revit__.Application.VersionNumber) > 2014:
        cursheet = revit.uidoc.ActiveGraphicalView
        for v in selSheets:
            if cursheet.Id == v.Id:
                selSheets.remove(v)
    else:
        cursheet = selSheets[0]
        selSheets.remove(cursheet)

    revit.uidoc.ActiveView = cursheet
    sel = revit.pick_elements()
    for el in sel:
        selViewports.append(revit.doc.GetElement(el))

    if len(selViewports) > 0:
        with revit.Transaction('Copy Viewports to Sheets'):
            for sht in selSheets:
                existing_vps = [revit.doc.GetElement(x)
                                for x in sht.GetAllViewports()]
                existing_schedules = [x for x in allSheetedSchedules
                                      if x.OwnerViewId == sht.Id]
                for vp in selViewports:
                    if isinstance(vp, DB.Viewport):
                        # check if viewport already exists
                        # and update location and type
                        for exist_vp in existing_vps:
                            if vp.ViewId == exist_vp.ViewId:
                                exist_vp.SetBoxCenter(vp.GetBoxCenter())
                                exist_vp.ChangeTypeId(vp.GetTypeId())
                                break
                        # if not, create a new viewport
                        else:
                            new_vp = \
                                DB.Viewport.Create(revit.doc,
                                                   sht.Id,
                                                   vp.ViewId,
                                                   vp.GetBoxCenter())

                            new_vp.ChangeTypeId(vp.GetTypeId())
                    elif isinstance(vp, DB.ScheduleSheetInstance):
                        # check if schedule already exists
                        # and update location
                        for exist_sched in existing_schedules:
                            if vp.ScheduleId == exist_sched.ScheduleId:
                                exist_sched.Point = vp.Point
                                break
                        # if not, place the schedule
                        else:
                            DB.ScheduleSheetInstance.Create(revit.doc,
                                                            sht.Id,
                                                            vp.ScheduleId,
                                                            vp.Point)
    else:
        UI.TaskDialog.Show('pyrevit',
                           'At least one viewport must be selected.')
else:
    UI.TaskDialog.Show('pyrevit',
                       'At least one sheet must be selected.')
