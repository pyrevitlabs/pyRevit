from scriptutils import this_script
from revitutils import doc

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
            slopes[s].append(el.Id)
        else:
            slopes[s] = [el.Id]

for sl, elids in slopes.items():
    print('SLOPE: {0}'.format(sl))
    print('ROOF ELEMENTS WITH THIS SLOPE:')
    el_links = ''
    for elid in elids:
        el_links += this_script.output.linkify(elid)
    print(el_links)
    print('\n')
