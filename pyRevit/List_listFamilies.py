cl = FilteredElementCollector(doc)
list = [i for i in cl.OfClass(Family).ToElements() if i.FamilyCategory.Name == 'Doors']

for family in list:
	print('NAME: {0} CATEGORY: {1}'.format(	family.Name.ljust(50),
								family.FamilyCategory.Name.ljust(15)
	))