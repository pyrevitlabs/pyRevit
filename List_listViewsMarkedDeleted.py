from Autodesk.Revit.DB import *
# from Autodesk.Revit.DB.Architecture import *
# from Autodesk.Revit.DB.Analysis import *
# import Autodesk.Revit.UI

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
selection = list(__revit__.ActiveUIDocument.Selection.Elements)

cl_views = FilteredElementCollector(doc)
views = cl_views.OfCategory(BuiltInCategory.OST_Views).WhereElementIsNotElementType().ToElements()

count = 0

for v in views:
	if v.Parameter['View Type'] and v.Parameter['View Type'].AsString() and v.Parameter['View Type'].AsString().lower().rfind('del')!=-1:
		print('TYPE: {1}ID: {2} VIEW TYPE: {3} {0}'.format(
				v.ViewName.ljust(100),
				str(v.ViewType).ljust(15),
				str(v.Id).ljust(10),
				v.Parameter['View Type'].AsString().ljust(25)
			))
		count+=1

print('TOTAL OF {0} DELETED VIEWS FOUND.'.format(count))