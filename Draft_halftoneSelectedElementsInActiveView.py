from Autodesk.Revit.DB import Transaction
from Autodesk.Revit.DB import OverrideGraphicSettings
from Autodesk.Revit.DB import Group

doc = __revit__.ActiveUIDocument.Document
selection = list(__revit__.ActiveUIDocument.Selection.Elements)

__window__.Close()

with Transaction(doc,"Set Element Override") as t:
	t.Start()
	for el in selection:
		if isinstance(el, Group):
			for mem in el.GetMemberIds():
				selection.append(doc.GetElement(mem))
		ogs = OverrideGraphicSettings()
		ogs.SetHalftone(True)
		ogs.SetProjectionFillPatternVisible(False)
		doc.ActiveView.SetElementOverrides(el.Id, ogs);
	t.Commit()