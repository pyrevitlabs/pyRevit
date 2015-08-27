from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
selection = [ doc.GetElement( elId ) for elId in __revit__.ActiveUIDocument.Selection.GetElementIds() ]


cl = FilteredElementCollector(doc)
list = cl.OfCategory( BuiltInCategory.OST_Areas ).WhereElementIsNotElementType().ToElements()

for el in list:
		print('AREA NAME: {0} AREA NUMBER: {1} AREA ID: {2} LEVEL: {3} AREA: {4}'.format(
			el.LookupParameter('Name').AsString().ljust(30),
			el.LookupParameter('Number').AsString().ljust(10),
			el.Id,
			str(el.Level.Name).ljust(50),
			el.Area,
			))

print('\n\nTOTAL AREAS FOUND: {0}'.format(len(list)))