from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory, View

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

vps = []

cl_views = FilteredElementCollector(doc)
vps = cl_views.OfCategory( BuiltInCategory.OST_Viewports ).WhereElementIsNotElementType().ToElements()

for v in vps:
	print v.Name
	# phasep = v.LookupParameter('Phase')
	# underlayp = v.LookupParameter('Underlay')
	# print('TYPE: {1}ID: {2}TEMPLATE: {3}PHASE:{4} UNDERLAY:{5}  {0}'.format(
			# v.ViewName,
			# str(v.ViewType).ljust(20),
			# str(v.Id).ljust(10),
			# str(v.IsTemplate).ljust(10),
			# phasep.AsValueString().ljust(25) if phasep else '---'.ljust(25),
			# underlayp.AsValueString().ljust(25) if underlayp else '---'.ljust(25)
		# ))