__window__.Width = 1100
from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory, View

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
selection = [ doc.GetElement( elId ) for elId in __revit__.ActiveUIDocument.Selection.GetElementIds() ]

views = []

if len(selection) == 0:
	cl_views = FilteredElementCollector(doc)
	views = cl_views.OfCategory( BuiltInCategory.OST_Views ).WhereElementIsNotElementType().ToElements()
else:
	for sel in selection:
		if isinstance(sel, View):
			views.append(sel)

for v in views:
	phasep = v.LookupParameter('Phase')
	underlayp = v.LookupParameter('Underlay')
	print('TYPE: {1}ID: {2}TEMPLATE: {3}PHASE:{4} UNDERLAY:{5}  {0}'.format(
			v.ViewName,
			str(v.ViewType).ljust(20),
			str(v.Id).ljust(10),
			str(v.IsTemplate).ljust(10),
			phasep.AsValueString().ljust(25) if phasep else '---'.ljust(25),
			underlayp.AsValueString().ljust(25) if underlayp else '---'.ljust(25)
		))