from Autodesk.Revit.DB import *
from Autodesk.Revit.UI import TaskDialog
from Autodesk.Revit.UI.Selection import *

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
selection = list(__revit__.ActiveUIDocument.Selection.Elements)


selSheets = []
selViewports = []

curview = doc.ActiveView

for el in uidoc.Selection.Elements:
	if isinstance(el, ViewSheet):
		selSheets.append(el)

if len(selSheets) == 0:
	TaskDialog.Show('RevitPythonShell', 'You must select at least one sheet to add the selected viewports to.')
	__window__.Close()
elif len(selSheets) > 2:
	TaskDialog.Show('RevitPythonShell', 'Maximum of two sheets can only be selected.')
	__window__.Close()

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
				viewId = vp.ViewId
				vpCenter = vp.GetBoxCenter()
				vpTypeId = vp.GetTypeId()
				cursheet.DeleteViewport(vp)
				nvp = Viewport.Create( doc, sht.Id, viewId, vpCenter)
				nvp.ChangeTypeId( vpTypeId )

	t.Commit()