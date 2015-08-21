from Autodesk.Revit.DB import Transaction
from Autodesk.Revit.DB import OverrideGraphicSettings
from Autodesk.Revit.DB import LinePatternElement

__window__.Close()

doc = __revit__.ActiveUIDocument.Document
selection = list(__revit__.ActiveUIDocument.Selection.Elements)

with Transaction(doc,"Set Element to Solid Projection Line Pattern") as t:
	t.Start()
	for el in selection:
		if el.ViewSpecific:
			ogs = OverrideGraphicSettings()
			ogs.SetProjectionLinePatternId( LinePatternElement.GetSolidPatternId() )
			doc.ActiveView.SetElementOverrides(el.Id, ogs);
	t.Commit()