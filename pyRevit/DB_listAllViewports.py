from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory, View

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

vps = []

cl_views = FilteredElementCollector(doc)
vps = cl_views.OfCategory( BuiltInCategory.OST_Viewports ).WhereElementIsNotElementType().ToElements()

for v in vps:
	print('ID: {1}TYPE: {0}VIEWNAME: {2}'.format(
			v.Name.ljust(30),
			str(v.Id).ljust(10),
			doc.GetElement( v.ViewId ).ViewName
		))