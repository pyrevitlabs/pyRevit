from Autodesk.Revit.DB import FilteredElementCollector, SketchPlane, Transaction
doc = __revit__.ActiveUIDocument.Document

cl = FilteredElementCollector(doc)
list = [i for i in cl.OfClass(SketchPlane).ToElements()]

for gs in list:
	print('NAME: {0} ID: {1}'.format(	gs.Name.ljust(50), gs.Id ))
