from pyrevit import revit, DB, UI
from pyrevit import forms
from pyrevit import script


__title__ = 'Copy/Update Selected Viewports To Selected Sheets'

__doc__ = 'Open the source sheet. Select other sheets in Project Browser. '\
          'Run this script (Keep focus on Project Browser otherwise the ' \
          'current selection will not show the selected sheets). ' \
          'Select Viewports and push Finish button on the properties bar. ' \
          'The selected views will be added to the selected sheets. ' \
          'If the view or schedule already exists on that sheet, the ' \
          'location and viewport type will be updated.'


logger = script.get_logger()


def is_placable(view):
    if view and view.ViewType and view.ViewType in [DB.ViewType.Schedule,
                                                    DB.ViewType.DraftingView,
                                                    DB.ViewType.Legend,
                                                    DB.ViewType.CostReport,
                                                    DB.ViewType.LoadsReport,
                                                    DB.ViewType.ColumnSchedule,
                                                    DB.ViewType.PanelSchedule]:
        return True
    return False


def update_if_placed(vport, exst_vps):
    for exst_vp in exst_vps:
        if vport.ViewId == exst_vp.ViewId:
            exst_vp.SetBoxCenter(vport.GetBoxCenter())
            exst_vp.ChangeTypeId(vport.GetTypeId())
            return True
    return False


selViewports = []

allSheetedSchedules = DB.FilteredElementCollector(revit.doc)\
                        .OfClass(DB.ScheduleSheetInstance)\
                        .ToElements()


selSheets = forms.select_sheets(title='Select Target Sheets',
                                button_name='Select Sheets')

# get a list of viewports to be copied, updated
if selSheets and len(selSheets) > 0:
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
        selViewports.append(el)

    if len(selViewports) > 0:
        with revit.Transaction('Copy Viewports to Sheets'):
            for sht in selSheets:
                existing_vps = [revit.doc.GetElement(x)
                                for x in sht.GetAllViewports()]
                existing_schedules = [x for x in allSheetedSchedules
                                      if x.OwnerViewId == sht.Id]
                for vp in selViewports:
                    if isinstance(vp, DB.Viewport):
                        src_view = revit.doc.GetElement(vp.ViewId)
                        # check if viewport already exists
                        # and update location and type
                        if update_if_placed(vp, existing_vps):
                            break
                        # if not, create a new viewport
                        elif is_placable(src_view):
                            new_vp = \
                                DB.Viewport.Create(revit.doc,
                                                   sht.Id,
                                                   vp.ViewId,
                                                   vp.GetBoxCenter())

                            new_vp.ChangeTypeId(vp.GetTypeId())
                        else:
                            logger.warning('Skipping {}. This view type '
                                           'can not be placed on '
                                           'multiple sheets.'
                                           .format(src_view.ViewName))
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
