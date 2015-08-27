__window__.Close()
from Autodesk.Revit.DB import Transaction, OverrideGraphicSettings

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
selection = __revit__.ActiveUIDocument.Selection.GetElementIds()

with Transaction(doc, 'Reset Element Override') as t:
	t.Start()
	for elId in selection:
		ogs = OverrideGraphicSettings()
		doc.ActiveView.SetElementOverrides( elId, ogs )
	t.Commit()