from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory, RevisionCloud, ElementId
doc = __revit__.ActiveUIDocument.Document

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
selection = [ doc.GetElement( elId ) for elId in __revit__.ActiveUIDocument.Selection.GetElementIds() ]

selectedrevs = []
hasSelectedRevision = False
multipleRevs = False

for s in selection:
	if isinstance( s, RevisionCloud):
		selectedrevs.append( s.RevisionId.IntegerValue )

if len( selectedrevs ) > 1:
	multipleRevs = True

print('REVISED SHEETS:\n\nNAME\tNUMBER\n--------------------------------------------------------------------------')
# print('REVISED SHEETS:\n\nNAME\tNUMBER\t\t\t\tLast Revision Created by\n--------------------------------------------------------------------------')
cl_sheets = FilteredElementCollector(doc)
sheetsnotsorted = cl_sheets.OfCategory(BuiltInCategory.OST_Sheets).WhereElementIsNotElementType().ToElements()
sheets = sorted(sheetsnotsorted, key=lambda x: x.SheetNumber)

for s in sheets:
	hasSelectedRevision = False
	revs = s.GetAllRevisionIds()
	revIds = [x.IntegerValue for x in revs]
	for sr in selectedrevs:
		if sr in revIds:
			hasSelectedRevision = True
	if hasSelectedRevision:
		lastowner = ''
		# revcloudids = list( FilteredElementCollector( doc, s.Id ).OfClass( RevisionCloud ).WhereElementIsNotElementType().ToElementIds() )
		# if len( revcloudids ) > 0:
			# lastcloud = max( [ x.IntegerValue for x in revcloudids ] )
			# lastowner = doc.GetElement( ElementId( lastcloud )).LookupParameter( 'Edited by' ).AsString()
		print('{0}\t{1}\t{2}'
			.format(	s.Parameter['Sheet Number'].AsString(),
						s.Parameter['Sheet Name'].AsString(),
						lastowner,
			))
		if multipleRevs:
			for rev in revs:
				rev = doc.GetElement(rev)
				print('\tREV#: {0}\t\tDATE: {1}\t\tDESC:{2}'.format( rev.RevisionNumber, rev.RevisionDate, rev.Description ))