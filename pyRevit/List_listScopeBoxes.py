from Autodesk.Revit.DB import *
# from Autodesk.Revit.DB.Architecture import *
# from Autodesk.Revit.DB.Analysis import *
# import Autodesk.Revit.UI

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
selection = list(__revit__.ActiveUIDocument.Selection.Elements)


cl = FilteredElementCollector(doc)
scopeboxes = cl.OfCategory(BuiltInCategory.OST_VolumeOfInterest).WhereElementIsNotElementType().ToElements()

for el in scopeboxes:
	print('SCOPEBOX: {0}'.format( el.Name ) )
