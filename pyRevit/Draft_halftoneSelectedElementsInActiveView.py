__window__.Close()
from Autodesk.Revit.DB import Transaction, OverrideGraphicSettings, Group

doc = __revit__.ActiveUIDocument.Document
selection = [ doc.GetElement( elId ) for elId in __revit__.ActiveUIDocument.Selection.GetElementIds() ]


with Transaction(doc, 'Halftone Elements in View' ) as t:
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