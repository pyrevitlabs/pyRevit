from pyrevit import HOST_APP
from pyrevit import revit, DB, UI
from pyrevit import forms
from pyrevit import script


__doc__ = 'Open the source sheet. Run this script and select destination '\
          'sheet. Select Viewports and push Finish button on the '\
          'properties bar. The selected views will be MOVED to '\
          'the destination sheet.'


selViewports = []

dest_sheet = forms.select_sheets(title='Select Target Sheets',
                                 button_name='Select Sheets',
                                 multiple=False,
                                 include_placeholder=False,
                                 use_selection=True)

if dest_sheet:
    cursheet = revit.active_view
    sel = revit.pick_elements()
    for el in sel:
        selViewports.append(el)

    if len(selViewports) > 0:
        with revit.Transaction('Move Viewports'):
            for vp in selViewports:
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
