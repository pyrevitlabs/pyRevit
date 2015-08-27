from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory, ViewType

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

cl_views = FilteredElementCollector(doc)
allviews = cl_views.OfCategory( BuiltInCategory.OST_Views ).WhereElementIsNotElementType().ToElements()
views = filter( lambda x: (( x.ViewType != ViewType.DraftingView or x.ViewType != ViewType.ThreeD ) and not x.IsTemplate ), allviews)

viewList = []

for v in views:
	print('Searching {0} of type: {1}'.format( v.ViewName, str(v.ViewType).ljust(25) ))
	cl_els = FilteredElementCollector( doc, v.Id ).WhereElementIsNotElementType().ToElementIds()
	print('\tTotal found: {0}'.format( len( cl_els )))
	i = 0
	for elId in uidoc.Selection.GetElementIds():
		if elId in cl_els:
			i =+ 1
			viewList.append( v )
		print('\t{0} element(s) found.'.format( i ))

print('\n\nViews Containing the selected objects:')

for v in viewList:
	print('{0}{1}ID:{2}'.format( 	v.ViewName.ljust(45),
								str(v.ViewType).ljust(25),
								str(v.Id).ljust(10) ))