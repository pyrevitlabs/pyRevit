from pyrevit import revit, DB, UI
from pyrevit import forms


__doc__ = 'Opens the view associated to the selected viewport. '\
          'You can assign a shortcut to this tool and this is a '\
          'quick way top open the views when working on sheets.'


selection = revit.get_selection()

# Opens the associated view with the selected viewport on a sheet.
if len(selection) > 0 and isinstance(selection[0], DB.Viewport):
    vp = selection[0]
    vpid = vp.ViewId
    view = revit.doc.GetElement(vpid)
    revit.uidoc.ActiveView = view
else:
    forms.alert('Select a Viewport first')
