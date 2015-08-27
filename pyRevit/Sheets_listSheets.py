from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

cl_sheets = FilteredElementCollector(doc)
sheetsnotsorted = cl_sheets.OfCategory(BuiltInCategory.OST_Sheets).WhereElementIsNotElementType().ToElements()
sheets = sorted(sheetsnotsorted, key=lambda x: x.SheetNumber)

for s in sheets:
	print('NUMBER: {0}   NAME:{1}'
		.format(	s.Parameter['Sheet Number'].AsString().rjust(10),
					s.Parameter['Sheet Name'].AsString().ljust(50),
		))