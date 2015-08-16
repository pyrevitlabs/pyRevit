from Autodesk.Revit.DB import *
# from Autodesk.Revit.DB.Architecture import *
# from Autodesk.Revit.DB.Analysis import *
# import Autodesk.Revit.UI

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
selection = list(__revit__.ActiveUIDocument.Selection.Elements)


cl = FilteredElementCollector(doc)
clfurn = cl.OfCategory(BuiltInCategory.OST_Levels).WhereElementIsNotElementType()

for i in clfurn:
	print('Level ID:\t{1}\t\t\tName:\t{0}'.format(i.Name, i.Id.IntegerValue))
	