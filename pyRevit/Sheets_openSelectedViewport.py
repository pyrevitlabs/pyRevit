__window__.Close()
from Autodesk.Revit.DB import Viewport
from Autodesk.Revit.UI import TaskDialog

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
selection = [ doc.GetElement( elId ) for elId in __revit__.ActiveUIDocument.Selection.GetElementIds() ]

#Opens the associated view with the selected viewport on a sheet.
if len(selection) > 0 and isinstance(selection[0],Viewport):
	vp = selection[0]
	vpid = vp.ViewId
	view = doc.GetElement( vpid )
	uidoc.ActiveView = view
else:
	TaskDialog.Show('RevitPythonShell', 'Select a Viewport first')