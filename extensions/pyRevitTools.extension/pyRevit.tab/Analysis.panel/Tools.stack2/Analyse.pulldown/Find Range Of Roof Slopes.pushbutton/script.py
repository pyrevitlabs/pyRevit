"""Lists all roof slopes in the model."""
from pyrevit import script
from pyrevit import revit, DB


output = script.get_output()


rooflist = DB.FilteredElementCollector(revit.doc)\
             .OfCategory(DB.BuiltInCategory.OST_Roofs)\
             .WhereElementIsNotElementType().ToElements()


slopes = {}


for el in rooflist:
    slope_param = el.Parameter[DB.BuiltInParameter.ROOF_SLOPE]
    if slope_param:
        slope_value = slope_param.AsValueString()
        if slope_value in slopes.keys():
            slopes[slope_value].append(el.Id)
        else:
            slopes[slope_value] = [el.Id]

for sl, elids in slopes.items():
    print('SLOPE: {0}'.format(sl))
    print('ROOF ELEMENTS WITH THIS SLOPE:')
    el_links = ''
    for elid in elids:
        el_links += output.linkify(elid)
    print(el_links)
    print('\n')
