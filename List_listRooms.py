from Autodesk.Revit.DB import *
# from Autodesk.Revit.DB.Architecture import *
# from Autodesk.Revit.DB.Analysis import *
# import Autodesk.Revit.UI

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
selection = list(__revit__.ActiveUIDocument.Selection.Elements)


cl = FilteredElementCollector(doc)
list = cl.OfCategory(BuiltInCategory.OST_Rooms).WhereElementIsNotElementType().ToElements()

for el in list:
	# if 'BILL' in el.Parameter['Name'].AsString():
		print('ROOM NAME: {0} ROOM NUMBER: {1} ROOM ID: {2}'.format( el.Parameter['Name'].AsString().ljust(30), el.Parameter['Number'].AsString().ljust(20), el.Id))

print('\n\nTOTAL ROOMS FOUND: {0}'.format(len(list)))