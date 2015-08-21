from Autodesk.Revit.DB import *
from Autodesk.Revit.UI import TaskDialog
from Autodesk.Revit.UI.Selection import *

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
selection = list(__revit__.ActiveUIDocument.Selection.Elements)


selSheets = []
selViewports = []

#pick sheets from selection
for el in uidoc.Selection.Elements:
	if isinstance(el, ViewSheet):
		selSheets.append(el)

if len(selSheets) == 0:
	TaskDialog.Show('RevitPythonShell', 'At least one sheet must be selected.')
	__window__.Close()

if __revit__.Application.VersionNumber == '2015':
	cursheet = uidoc.ActiveGraphicalView
	for v in selSheets:
		if cursheet.Id == v.Id:
			selSheets.remove(v)
else:
	cursheet = selSheets[0]
	selSheets.remove(cursheet)

uidoc.ActiveView = cursheet
__window__.Close()
sel = uidoc.Selection.PickObjects(ObjectType.Element)
for el in sel:
	selViewports.append( doc.GetElement( el ) )

if len(selViewports) == 0:
	TaskDialog.Show('RevitPythonShell', 'At least one viewport must be selected.')
	__window__.Close()


with Transaction(doc, 'Add Viewports to Sheets') as t:
	t.Start()

	for sht in selSheets:
		for vp in selViewports:
			if isinstance(vp, Viewport):
				nvp = Viewport.Create( doc, sht.Id, vp.ViewId, vp.GetBoxCenter() )
				nvp.ChangeTypeId( vp.GetTypeId() )
			elif isinstance(vp, ScheduleSheetInstance):
				ScheduleSheetInstance.Create( doc, sht.Id, vp.ScheduleId, vp.Point )

	t.Commit()