__window__.Close()
from Autodesk.Revit.DB import Transaction
from Autodesk.Revit.DB import DetailElementOrderUtils as eo

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

with Transaction( doc, 'Bring Selected To Front' ) as t:
	t.Start()
	for elId in uidoc.Selection.GetElementIds():
		try:
			eo.BringForward( doc, doc.ActiveView, elId )
		except:
			continue
	t.Commit()