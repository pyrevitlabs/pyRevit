__window__.Width = 1200
from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory, View

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
# selection = [ doc.GetElement( elId ) for elId in __revit__.ActiveUIDocument.Selection.GetElementIds() ]

views = []

cl_views = FilteredElementCollector(doc)
views = cl_views.OfCategory( BuiltInCategory.OST_Views ).WhereElementIsNotElementType().ToElements()

mviews = []
dviews = []

for v in views:
	if 'drafting' in str( v.ViewType ).lower():
		dviews.append( v )
	else:
		mviews.append( v )

print('UNREFERENCED DRAFTING VIEWS-----------------------------------------------------------------------------------')
for v in dviews:
	phasep = v.LookupParameter('Phase')
	sheetnum = v.LookupParameter('Sheet Number')
	detnum = v.LookupParameter('Detail Number')
	refsheet = v.LookupParameter('Referencing Sheet')
	refviewport = v.LookupParameter('Referencing Detail')
	if refsheet and refviewport and refsheet.AsString() != '' and refviewport.AsString() != '':
		continue
	else:
		print('TYPE: {1}ID: {2}TEMPLATE: {3}PHASE:{4}  {0}\nPLACED ON DETAIL/SHEET: {6} / {5}\n'.format(
				v.ViewName,
				str( v.ViewType ).ljust(20),
				str(v.Id).ljust(10),
				str(v.IsTemplate).ljust(10),
				phasep.AsValueString().ljust(25) if phasep else '---'.ljust(25),
				sheetnum.AsString() if sheetnum else '-',
				detnum.AsString() if detnum else '-',
			))

print('\n\n\nUNREFERENCED MODEL VIEWS-----------------------------------------------------------------------------------')
for v in mviews:
	phasep = v.LookupParameter('Phase')
	sheetnum = v.LookupParameter('Sheet Number')
	detnum = v.LookupParameter('Detail Number')
	refsheet = v.LookupParameter('Referencing Sheet')
	refviewport = v.LookupParameter('Referencing Detail')
	if refsheet and refviewport and refsheet.AsString() != '' and refviewport.AsString() != '':
		continue
	else:
		print('TYPE: {1}ID: {2}TEMPLATE: {3}PHASE:{4}  {0}\nPLACED ON DETAIL/SHEET: {6} / {5}\n'.format(
				v.ViewName,
				str( v.ViewType ).ljust(20),
				str(v.Id).ljust(10),
				str(v.IsTemplate).ljust(10),
				phasep.AsValueString().ljust(25) if phasep else '---'.ljust(25),
				sheetnum.AsString() if sheetnum else '-',
				detnum.AsString() if detnum else '-',
			))
