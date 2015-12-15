__window__.Width = 1200
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

views = list( views )
dviews = []

for v in views:
	if 'drafting' in str( v.ViewType ).lower():
		dviews.append( v )
		views.remove( v )

print('UNREFERENCED DRAFTING VIEWS-----------------------------------------------------------------------------------')
for v in dviews:
	phasep = v.LookupParameter('Phase')
	refsheet = v.LookupParameter('Referencing Sheet')
	refviewport = v.LookupParameter('Referencing Detail')
	if refsheet and refviewport and refsheet.HasValue and refviewport.HasValue:
		underlayp = v.LookupParameter('Underlay')
		print('TYPE: {1}ID: {2}TEMPLATE: {3}PHASE:{4}  {0}\nPLACED ON DETAIL/SHEET: {7} / {6}\n'.format(
				v.ViewName,
				str( v.ViewType ).ljust(20),
				str(v.Id).ljust(10),
				str(v.IsTemplate).ljust(10),
				phasep.AsValueString().ljust(25) if phasep else '---'.ljust(25),
				underlayp.AsValueString().ljust(25) if underlayp else '---'.ljust(25),
				v.LookupParameter('Sheet Number').AsString(),
				v.LookupParameter('Detail Number').AsString()
			))

print('\n\n\nUNREFERENCED MODEL VIEWS-----------------------------------------------------------------------------------')
for v in views:
	phasep = v.LookupParameter('Phase')
	refsheet = v.LookupParameter('Referencing Sheet')
	refviewport = v.LookupParameter('Referencing Detail')
	if refsheet and refviewport and refsheet.HasValue and refviewport.HasValue:
		underlayp = v.LookupParameter('Underlay')
		print('TYPE: {1}ID: {2}TEMPLATE: {3}PHASE:{4}  {0}\nPLACED ON DETAIL/SHEET: {7} / {6}\n'.format(
				v.ViewName,
				str( v.ViewType ).ljust(20),
				str(v.Id).ljust(10),
				str(v.IsTemplate).ljust(10),
				phasep.AsValueString().ljust(25) if phasep else '---'.ljust(25),
				underlayp.AsValueString().ljust(25) if underlayp else '---'.ljust(25),
				v.LookupParameter('Sheet Number').AsString(),
				v.LookupParameter('Detail Number').AsString()
			))