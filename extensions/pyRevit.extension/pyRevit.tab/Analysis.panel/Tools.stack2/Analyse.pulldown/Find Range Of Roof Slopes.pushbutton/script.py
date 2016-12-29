from scriptutils import doc

# noinspection PyUnresolvedReferences
from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory


__doc__ = 'Lists all roof slopes in the model.'


rooflist = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Roofs)\
                                        .WhereElementIsNotElementType().ToElements()

slopes = dict()

for el in rooflist:
    p = el.LookupParameter('Slope')
    if p:
        s = p.AsValueString()
        if s in slopes.keys():
            slopes[s].append(el.Id.IntegerValue)
        else:
            slopes[s] = [el.Id.IntegerValue]

for sl, elid in slopes.items():
    print('SLOPE: {0}'.format(sl))
    print('ROOF ELEMENTS WITH THIS SLOPE:')
    print(elid)
    print('\n')
