from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory, ViewSheet
doc = __revit__.ActiveUIDocument.Document


cl = FilteredElementCollector(doc)
revs = cl.OfCategory(BuiltInCategory.OST_RevisionClouds).WhereElementIsNotElementType()

for rev in revs:
	parent = doc.GetElement( rev.OwnerViewId )
	if isinstance(parent, ViewSheet):
		print('REV#: {0}\t\tID: {3}\t\tON SHEET: {1} {2}'.format( doc.GetElement( rev.RevisionId ).RevisionNumber, parent.SheetNumber, parent.Name, rev.Id ))
	else:
		print('REV#: {0}\t\tID: {2}\t\tON VIEW: {1}'.format( doc.GetElement( rev.RevisionId ).RevisionNumber, parent.ViewName, rev.Id ))
