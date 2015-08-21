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
		ogs = OverrideGraphicSettings()
		ogs.SetProjectionLineStyleId()
		doc.ActiveView.SetElementOverrides(el.Id, ogs);
	t.Commit()