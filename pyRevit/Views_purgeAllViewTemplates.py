__window__.Width = 1100
from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory, View, Transaction

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

cl_views = FilteredElementCollector(doc)
views = cl_views.OfCategory( BuiltInCategory.OST_Views ).WhereElementIsNotElementType().ToElements()

vtbd = []

for v in views:
	if v.IsTemplate:
		print('ID: {1}		{0}'.format(
				v.ViewName,
				str(v.Id).ljust(10),
			))
		vtbd.append( v )

t = Transaction( doc, 'Remove All View Templates' )
t.Start()

for v in vtbd:
	doc.Delete( v.Id )

t.Commit()