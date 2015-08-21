__window__.Hide()

from Autodesk.Revit.DB import *
from Autodesk.Revit.UI import TaskDialog
from Autodesk.Revit.UI.Selection import ObjectType

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
curview = doc.ActiveView

if not isinstance(curview, ViewSheet):
	TaskDialog.Show('RevitPythonShell', 'You must be on a sheet to use this tool.')
	__window__.Close()

vports = { int(vp.Parameter['Detail Number'].AsString()):vp for vp in curview.Views if vp.Parameter['Detail Number']}
maxNum = max( vports.keys() )

with Transaction(doc, 'Re-number Viewports') as t:
	t.Start()

	sel = []
	while len(sel) < len(vports):
		try:
			el = doc.GetElement( uidoc.Selection.PickObject(ObjectType.Element) )
			if isinstance(el,Viewport):
				sel.append( doc.GetElement(el.ViewId) )
		except:
			break

	for i in range(1, len(sel)+1 ):
		try:
			vports[i].Parameter['Detail Number'].Set( str(maxNum + i) )
		except KeyError:
			continue

	for i,el in enumerate(sel):
		el.Parameter['Detail Number'].Set( str(i+1) )

	t.Commit()

__window__.Close()
