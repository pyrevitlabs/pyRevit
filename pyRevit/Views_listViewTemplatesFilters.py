__window__.Width = 1100
from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory, View

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

cl_views = FilteredElementCollector(doc)
views = cl_views.OfCategory( BuiltInCategory.OST_Views ).WhereElementIsNotElementType().ToElements()

for v in views:
	if v.IsTemplate:
		print('\nID: {1}\t{0}'.format(
				v.ViewName,
				str(v.Id).ljust(10),
			))
		filters = v.GetFilters()
		for fl in filters:
			print( '\t\t\tID: {0}\t{1}'.format( fl, doc.GetElement( fl ).Name ))