__window__.Width = 1100
from Autodesk.Revit.DB import FilteredElementCollector, Transaction, BuiltInCategory, ElementId
from Autodesk.Revit.UI import TaskDialog, TaskDialogCommonButtons, TaskDialogResult

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
viewlist = FilteredElementCollector(doc).OfCategory( BuiltInCategory.OST_Views ).WhereElementIsNotElementType().ToElements()

vtemp = set()
usedvtemp = set()
views = []

for v in viewlist:
	if v.IsTemplate and 'master' not in v.ViewName.lower():
		vtemp.add( v.Id.IntegerValue )
	else:
		views.append( v )

for v in views:
	vtid = v.ViewTemplateId.IntegerValue
	if vtid > 0:
		usedvtemp.add( vtid )

unusedvtemp = vtemp - usedvtemp


t = Transaction( doc, 'Purge Unused View Templates' )
t.Start()

for vid in unusedvtemp:
	view = doc.GetElement( ElementId( vid ))
	print view.ViewName

res = TaskDialog.Show('RevitPythonShell',
				'Are you sure you want to remove these view templates?',
				TaskDialogCommonButtons.Yes | TaskDialogCommonButtons.Cancel)

if res == TaskDialogResult.Yes:
	for v in unusedvtemp:
		doc.Delete( ElementId( v ))
else:
	print('----------- Purge Cancelled --------------')

t.Commit()