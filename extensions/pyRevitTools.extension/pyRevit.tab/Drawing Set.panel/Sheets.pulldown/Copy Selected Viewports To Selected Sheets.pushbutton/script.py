from pyrevit import revit, DB, UI
from pyrevit import forms
from pyrevit import script
import sheet_tools_utils

__title__ = 'Copy/Update Selected Viewports To Selected Sheets'

__doc__ = 'Open the source sheet. Run this script and select destination '\
          'sheets. Select Viewports and push Finish button on the '\
          'properties bar. The selected views will be added to the '\
          'destination sheets. If the view or schedule already exists on '\
          'that sheet, the location and type will be updated.'


logger = script.get_logger()


selViewports = []

allSheetedSchedules = DB.FilteredElementCollector(revit.doc)\
                        .OfClass(DB.ScheduleSheetInstance)\
                        .ToElements()


selected_sheets = forms.select_sheets(title='Select Target Sheets',
                                      include_placeholder=False,
                                      button_name='Select Sheets')

# get a list of viewports to be copied, updated
if selected_sheets and len(selected_sheets) > 0:
    if int(__revit__.Application.VersionNumber) > 2014:
        cursheet = revit.uidoc.ActiveGraphicalView
        for v in selected_sheets:
            if cursheet.Id == v.Id:
                selected_sheets.remove(v)
    else:
        cursheet = selected_sheets[0]
        selected_sheets.remove(cursheet)

    revit.uidoc.ActiveView = cursheet
    selected_vps = revit.pick_elements()

    if selected_vps:
        with revit.Transaction('Copy Viewports to Sheets'):
            for sht in selected_sheets:
                existing_vps = [revit.doc.GetElement(x)
                                for x in sht.GetAllViewports()]
                existing_schedules = [x for x in allSheetedSchedules
                                      if x.OwnerViewId == sht.Id]
                for vp in selected_vps:
                    sheet_tools_utils.copy_viewport(vp, 
                                                    sht, 
                                                    existing_vps, 
                                                    existing_schedules)
    else:
        forms.alert('At least one viewport must be selected.')
else:
    forms.alert('At least one sheet must be selected.')
