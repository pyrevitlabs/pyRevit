__window__.Width = 1100
__doc__ = 'Deletes all view parameter filters that has not been listed on any views. This includes sheets as well.'
from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory, View, ParameterFilterElement, Transaction, ElementId

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

views = FilteredElementCollector(doc).OfClass( View ).WhereElementIsNotElementType().ToElements()
filters = FilteredElementCollector(doc).OfClass( ParameterFilterElement ).ToElements()

usedFiltersSet = set()
allFilters = set()
for flt in filters:
	allFilters.add( flt.Id.IntegerValue )

for v in views:
	try:
		filters = v.GetFilters()
		for flid in filters:
			usedFiltersSet.add( flid.IntegerValue )
	except:
		continue

unusedFilters = allFilters - usedFiltersSet

t = Transaction(doc, 'Purge Unused Filters') 
t.Start()

for flid in unusedFilters:
	fl = doc.GetElement( ElementId( flid ) )
	print( 'ID: {0}\t{1}'.format( fl.Id, fl.Name ))
	doc.Delete( ElementId( flid ) )

t.Commit()