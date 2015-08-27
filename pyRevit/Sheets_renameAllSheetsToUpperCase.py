from Autodesk.Revit.DB import Transaction, FilteredElementCollector, BuiltInCategory

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

cl_views = FilteredElementCollector(doc)
views = cl_views.OfCategory(BuiltInCategory.OST_Sheets).WhereElementIsNotElementType().ToElements()
sheets = sorted(views, key=lambda x: x.SheetNumber)

t = Transaction(doc, 'Rename Sheets to Upper') 
t.Start()

for el in sheets:
	name = el.Parameter['Sheet Name'].AsString()
	name = name.upper()
	print('RENAMING:\t{0}\n      to:\t{1}\n'.format(name, name.upper()))
	el.Parameter['Sheet Name'].Set(name)

t.Commit()