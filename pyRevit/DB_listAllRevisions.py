from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory
doc = __revit__.ActiveUIDocument.Document


cl = FilteredElementCollector(doc)
revs = cl.OfCategory(BuiltInCategory.OST_Revisions).WhereElementIsNotElementType()

for rev in revs:
	print('{0}\tREV#: {1}\t\tDATE: {2}\t\tTYPE:{3}\t\tDESC: {4}'.format( rev.SequenceNumber, rev.RevisionNumber, rev.RevisionDate, rev.NumberType.ToString(), rev.Description))
