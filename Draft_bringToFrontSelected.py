from Autodesk.Revit.DB import DetailElementOrderUtils as eo

with Transaction(doc,"Bring Selected To Front") as t:
	t.Start()
	for el in selection:
		eo.BringForward(doc, doc.ActiveView, el.Id)
	t.Commit()