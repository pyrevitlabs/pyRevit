__window__.Close()
from Autodesk.Revit.DB import Transaction, OverrideGraphicSettings, LinePatternElement

doc = __revit__.ActiveUIDocument.Document
selection = [ doc.GetElement( elId ) for elId in __revit__.ActiveUIDocument.Selection.GetElementIds() ]

with Transaction(doc,"Set Element to Solid Projection Line Pattern") as t:
	t.Start()
	for el in selection:
		if el.ViewSpecific:
			ogs = OverrideGraphicSettings()
			ogs.SetProjectionLinePatternId( LinePatternElement.GetSolidPatternId() )
			doc.ActiveView.SetElementOverrides( el.Id, ogs );
	t.Commit()