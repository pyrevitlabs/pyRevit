from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory
doc = __revit__.ActiveUIDocument.Document

print('LIST OF REVISIONS:')
cl = FilteredElementCollector(doc)
revs = cl.OfCategory(BuiltInCategory.OST_Revisions).WhereElementIsNotElementType()
for rev in revs:
	print('{0}\tREV#: {1}\t\tDATE: {2}\t\tTYPE:{3}\t\tDESC: {4}'.format( rev.SequenceNumber, rev.RevisionNumber, rev.RevisionDate, rev.NumberType.ToString(), rev.Description))

print('\n\nREVISED SHEETS:\n\nNAME\tNUMBER\n--------------------------------------------------------------------------')
cl_sheets = FilteredElementCollector(doc)
sheetsnotsorted = cl_sheets.OfCategory(BuiltInCategory.OST_Sheets).WhereElementIsNotElementType().ToElements()
sheets = sorted(sheetsnotsorted, key=lambda x: x.SheetNumber)

for s in sheets:
	revs = s.GetAllRevisionIds()
	if len(revs) > 0:
		print('{0}\t{1}'
			.format(	s.Parameter['Sheet Number'].AsString(),
						s.Parameter['Sheet Name'].AsString(),
			))
		for rev in revs:
			rev = doc.GetElement(rev)
			print('\tREV#: {0}\t\tDATE: {1}\t\tDESC:{2}'.format( rev.RevisionNumber, rev.RevisionDate, rev.Description ))