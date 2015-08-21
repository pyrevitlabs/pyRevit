from Autodesk.Revit.DB import View

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
selection = list(__revit__.ActiveUIDocument.Selection.Elements)

el = selection[0]

for i in range(0, el.CurrentViewCount):
	v = doc.GetElement( el.GetViewId(i) )
	print('DETAIL #: {4}\tTYPE: {1}ID: {2}TEMPLATE: {3}  {0}'.format(
			v.ViewName.ljust(100),
			str(v.ViewType).ljust(15),
			str(v.Id).ljust(10),
			str(v.IsTemplate).ljust(10),
			v.LookupParameter('Detail Number').AsString()
		))