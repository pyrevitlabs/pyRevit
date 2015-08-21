from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory, View
# from Autodesk.Revit.DB.Architecture import *
# from Autodesk.Revit.DB.Analysis import *
# import Autodesk.Revit.UI

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
selection = list(__revit__.ActiveUIDocument.Selection.Elements)

views = []

if len(selection) == 0:
	cl_views = FilteredElementCollector(doc)
	views = cl_views.OfCategory(BuiltInCategory.OST_Views).WhereElementIsNotElementType().ToElements()
else:
	for sel in selection:
		if isinstance(sel, View):
			views.append(sel)

for v in views:
	print('TYPE: {1}ID: {2}TEMPLATE: {3}PHASE:{4} UNDERLAY:{5}  {0}'.format(
			v.ViewName.ljust(100),
			str(v.ViewType).ljust(15),
			str(v.Id).ljust(10),
			str(v.IsTemplate).ljust(10),
			v.Parameter['Phase'].AsValueString().ljust(25) if v.Parameter['Phase'] else '---'.ljust(25),
			v.Parameter['Underlay'].AsValueString().ljust(25) if v.Parameter['Underlay'] else '---'.ljust(25)
		))