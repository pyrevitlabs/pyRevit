from Autodesk.Revit.DB import *
# from Autodesk.Revit.DB.Architecture import *
# from Autodesk.Revit.DB.Analysis import *
# import Autodesk.Revit.UI

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
selection = list(__revit__.ActiveUIDocument.Selection.Elements)

cl_views = FilteredElementCollector(doc)
views = cl_views.OfCategory(BuiltInCategory.OST_Views).WhereElementIsNotElementType().ToElements()

t = Transaction(doc, 'Batch Capitalize View Locations') 
t.Start()

for el in views:
	pvloc = el.GetParameters('View Location')[0]
	#print(pvloc, el.ViewName, el.ViewType)
	if pvloc and not el.IsTemplate and el.ViewType != ViewType.Legend:
		vloc = pvloc.AsString()
		if vloc[0] == '*':
			continue
		print('Renaming:\t{0}\n      to:\t{1}\n'.format(vloc, vloc.upper()))
		try:
			pvloc.Set( vloc.upper() )
		except Exception:
			continue

t.Commit()