from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
selection = [ doc.GetElement( elId ) for elId in __revit__.ActiveUIDocument.Selection.GetElementIds() ]


cl = FilteredElementCollector(doc)
list = cl.OfCategory(BuiltInCategory.OST_Rooms).WhereElementIsNotElementType().ToElements()

for el in list:
	print('ROOM NAME: {0} ROOM NUMBER: {1} ROOM ID: {2}'.format(	el.LookupParameter('Name').AsString().ljust(30),
																	el.LookupParameter('Number').AsString().ljust(20),
																	el.Id))

print('\n\nTOTAL ROOMS FOUND: {0}'.format(len(list)))