cl_views = FilteredElementCollector(doc)
allviews = cl_views.OfCategory(BuiltInCategory.OST_Views).WhereElementIsNotElementType().ToElements()
views = filter(lambda x: ((x.ViewType != ViewType.DraftingView or x.ViewType != ViewType.ThreeD) and not x.IsTemplate), allviews)

res = []

for v in views:
	print('Searching {0}...'.format(r.ViewName))
	cl_els = FilteredElementCollector( doc, r.Id ).WhereElementIsNotElementType().ToElementIds()
	print('\tTotal found: {0}'.format(len(cl_els)))
	i = 0
	for el in uidoc.Selection.Elements:
		if el.Id in cl_els:
			i=+1
			res.append(v)
		print('\t{0} element(s) found.'.format(i))

print('\n\nViews Containing the selected objects:')
for r in res:
	print('{0}{1}{2}'.format(r.ViewName.ljust(45), str(r.ViewType).ljust(15), str(r.Id).ljust(10)))