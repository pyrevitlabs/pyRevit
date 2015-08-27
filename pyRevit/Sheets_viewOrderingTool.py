__window__.Hide()
from Autodesk.Revit.DB import Transaction, ViewSheet, Viewport
from Autodesk.Revit.UI import TaskDialog
from Autodesk.Revit.UI.Selection import ObjectType

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
curview = doc.ActiveView

if not isinstance(curview, ViewSheet):
	TaskDialog.Show('RevitPythonShell', 'You must be on a sheet to use this tool.')
	__window__.Close()

viewports = []
for vpId in curview.GetAllViewports():
	viewports.append( doc.GetElement( vpId ))

vports = { int(vp.LookupParameter('Detail Number').AsString()):vp for vp in viewports if vp.LookupParameter('Detail Number')}
maxNum = max( vports.keys() )

with Transaction(doc, 'Re-number Viewports') as t:
	t.Start()

	sel = []
	while len(sel) < len(vports):
		try:
			el = doc.GetElement( uidoc.Selection.PickObject( ObjectType.Element ))
			if isinstance(el,Viewport):
				sel.append( doc.GetElement(el.ViewId) )
		except:
			break

	for i in range(1, len(sel)+1 ):
		try:
			vports[i].LookupParameter('Detail Number').Set( str(maxNum + i) )
		except KeyError:
			continue

	for i,el in enumerate(sel):
		el.LookupParameter('Detail Number').Set( str(i+1) )

	t.Commit()

__window__.Close()
