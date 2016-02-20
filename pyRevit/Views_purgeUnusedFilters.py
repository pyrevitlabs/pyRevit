__window__.Width = 1100
from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory, View, ParameterFilterElement, Transaction, ElementId

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

views = FilteredElementCollector(doc).OfCategory( BuiltInCategory.OST_Views ).WhereElementIsNotElementType().ToElements()
filters = FilteredElementCollector(doc).OfClass( ParameterFilterElement ).ToElements()

usedFiltersSet = set()
allFilters = set()
for flt in filters:
	allFilters.add( flt.Id.IntegerValue )

for v in views:
	# if v.IsTemplate:
		# print('\nID: {1}\t{0}'.format(
				# v.ViewName,
				# str(v.Id).ljust(10),
			# ))
	filters = v.GetFilters()
	for flid in filters:
		usedFiltersSet.add( flid.IntegerValue )

unusedFilters = allFilters - usedFiltersSet

t = Transaction(doc, 'Purge Unused Filters') 
t.Start()

for flid in unusedFilters:
	fl = doc.GetElement( ElementId( flid ) )
	print( 'ID: {0}\t{1}'.format( fl, fl.Name ))
	doc.Delete( ElementId( flid ) )

t.Commit()