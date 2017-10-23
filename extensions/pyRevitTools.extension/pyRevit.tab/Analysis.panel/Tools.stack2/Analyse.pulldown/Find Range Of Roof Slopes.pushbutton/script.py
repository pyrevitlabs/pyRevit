"""Lists all roof slopes in the model."""

from pyrevit import script
from pyrevit import revit, DB


output = script.get_output()


rooflist = DB.FilteredElementCollector(revit.doc)\
             .OfCategory(DB.BuiltInCategory.OST_Roofs)\
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
        el_links += output.linkify(elid)
    print(el_links)
    print('\n')
