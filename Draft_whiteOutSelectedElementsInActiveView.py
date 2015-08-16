from Autodesk.Revit.DB import *
# from Autodesk.Revit.DB.Architecture import *
# from Autodesk.Revit.DB.Analysis import *
# import Autodesk.Revit.UI

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
selection = list(__revit__.ActiveUIDocument.Selection.Elements)

# id = uidoc.Selection.PickObject(ObjectType.Element,"Select an element").ElementId
with Transaction(doc,"Set Element Override") as t:
	t.Start()
	for el in selection:
		if el.ViewSpecific:
			continue
		elif isinstance(el, Group):
			for mem in el.GetMemberIds():
				selection.append(doc.GetElement(mem))
		ogs = OverrideGraphicSettings()
		ogs.SetProjectionLineColor(Color(255,255,255))
		doc.ActiveView.SetElementOverrides(el.Id, ogs);
	t.Commit()