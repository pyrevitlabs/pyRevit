from Autodesk.Revit.DB import FilteredElementCollector, GraphicsStyle, Transaction
doc = __revit__.ActiveUIDocument.Document

cl = FilteredElementCollector(doc)
list = [i for i in cl.OfClass(GraphicsStyle).ToElements()]

for gs in list:
	if gs.GraphicsStyleCategory.Parent:
		parent = gs.GraphicsStyleCategory.Parent.Name
	else:
		parent = '---'
	if gs.GraphicsStyleCategory.GetHashCode() > 0:
		print('NAME: {0} CATEGORY:{2} PARENT: {3} ID: {1}'.format(	gs.Name.ljust(50),
									gs.Id,
									gs.GraphicsStyleCategory.Name.ljust(50),
									parent.ljust(50),
		))
