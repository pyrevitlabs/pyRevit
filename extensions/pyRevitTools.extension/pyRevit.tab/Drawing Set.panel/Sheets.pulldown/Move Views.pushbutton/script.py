from pyrevit import HOST_APP
from pyrevit import revit, DB, UI
from pyrevit import forms
from pyrevit import script


cursheet = revit.active_view
forms.check_viewtype(cursheet, DB.ViewType.DrawingSheet, exitscript=True)

dest_sheet = forms.select_sheets(title='Select Target Sheets',
                                 button_name='Select Sheets',
                                 multiple=False,
                                 include_placeholder=False,
                                 use_selection=True)

selected_vports = []
if dest_sheet:
    sel = revit.pick_elements()
    for el in sel:
        selected_vports.append(el)

    if len(selected_vports) > 0:
        with revit.Transaction('Move Viewports'):
            for vp in selected_vports:
                if isinstance(vp, DB.Viewport):
                    viewId = vp.ViewId
                    vpCenter = vp.GetBoxCenter()
                    vpTypeId = vp.GetTypeId()
                    cursheet.DeleteViewport(vp)
                    nvp = DB.Viewport.Create(revit.doc,
                                             dest_sheet.Id,
                                             viewId,
                                             vpCenter)
                    nvp.ChangeTypeId(vpTypeId)
                elif isinstance(vp, DB.ScheduleSheetInstance):
                    nvp = \
                        DB.ScheduleSheetInstance.Create(
                            revit.doc, dest_sheet.Id, vp.ScheduleId, vp.Point
                            )
                    revit.doc.Delete(vp.Id)
    else:
        forms.alert('At least one viewport must be selected.')
else:
    forms.alert('You must select at least one sheet to add '
                'the selected viewports to.')
