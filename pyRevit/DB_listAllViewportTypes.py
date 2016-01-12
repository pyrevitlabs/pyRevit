from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory, Element, ElementType

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

vps = []

cl_views = FilteredElementCollector(doc)
vptypes = cl_views.OfClass( ElementType ).ToElements()

for type in vptypes:
	if type.FamilyName == 'Viewport':
		print('ID: {1}TYPE: {0}'.format(
				Element.Name.GetValue(type),
				str(type.Id).ljust(10),
			))