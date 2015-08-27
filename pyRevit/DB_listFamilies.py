from Autodesk.Revit.DB import FilteredElementCollector, Family
doc = __revit__.ActiveUIDocument.Document

cl = FilteredElementCollector(doc)
list = [i for i in cl.OfClass(Family).ToElements()]

for family in list:
	print('NAME: {0} CATEGORY: {1}'.format(	family.Name.ljust(50),
								family.FamilyCategory.Name.ljust(15)
	))