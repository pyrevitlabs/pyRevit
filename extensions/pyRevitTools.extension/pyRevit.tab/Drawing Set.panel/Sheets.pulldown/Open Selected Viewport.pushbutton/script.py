from pyrevit import revit, DB, UI
from pyrevit import forms


selection = revit.get_selection()

# Opens the associated view with the selected viewport on a sheet.
if len(selection) > 0 and isinstance(selection[0], DB.Viewport):
    vp = selection[0]
    vpid = vp.ViewId
    view = revit.doc.GetElement(vpid)
    revit.uidoc.ActiveView = view
else:
    forms.alert('Select a Viewport first')
