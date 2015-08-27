from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
selection = [ doc.GetElement( elId ) for elId in __revit__.ActiveUIDocument.Selection.GetElementIds() ]


cl = FilteredElementCollector(doc)
list = cl.OfCategory(BuiltInCategory.OST_Grids).WhereElementIsNotElementType().ToElements()

for el in list:
		print('GRID: {0} ID: {1}'.format(
			el.Name,
			el.Id,
			))