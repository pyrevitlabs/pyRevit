from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory
doc = __revit__.ActiveUIDocument.Document

cl_views = FilteredElementCollector(doc)
shts = cl_views.OfCategory(BuiltInCategory.OST_Sheets).WhereElementIsNotElementType().ToElements()
sheets = sorted(shts, key=lambda x: x.SheetNumber)

curview = doc.ActiveView
count = 0

print('Searching All Sheets for {0} ID:{1}\n'.format( curview.Name, curview.Id ))
for s in sheets:
	vpsIds = [doc.GetElement(x).ViewId for x in s.GetAllViewports()]
	if curview.Id in vpsIds:
		count +=1
		print('NUMBER: {0}   NAME:{1}'
			.format(	s.LookupParameter('Sheet Number').AsString().rjust(10),
						s.LookupParameter('Sheet Name').AsString().ljust(50),
			))

print('\n\nView is referenced on {0} sheets.'.format(count))