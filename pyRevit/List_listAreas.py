from Autodesk.Revit.DB import *
# from Autodesk.Revit.DB.Architecture import *
# from Autodesk.Revit.DB.Analysis import *
# import Autodesk.Revit.UI

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
selection = list(__revit__.ActiveUIDocument.Selection.Elements)


cl = FilteredElementCollector(doc)
list = cl.OfCategory(BuiltInCategory.OST_Areas).WhereElementIsNotElementType().ToElements()

for el in list:
		print('AREA NAME: {0} AREA NUMBER: {1} AREA ID: {2} LEVEL: {3} AREA: {4}'.format(
			el.ParametersMap['Name'].AsString().ljust(30),
			el.ParametersMap['Number'].AsString().ljust(10),
			el.Id,
			str(el.Level.Name).ljust(50),
			el.Area,
			))

print('\n\nTOTAL AREAS FOUND: {0}'.format(len(list)))