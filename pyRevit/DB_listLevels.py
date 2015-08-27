from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
selection = [ doc.GetElement( elId ) for elId in __revit__.ActiveUIDocument.Selection.GetElementIds() ]


cl = FilteredElementCollector(doc)
list = cl.OfCategory(BuiltInCategory.OST_Levels).WhereElementIsNotElementType()

for i in list:
	print('Level ID:\t{1}\t\t\tName:\t{0}'.format(i.Name, i.Id.IntegerValue))
	