"""Lists all roof slopes in the model."""
#pylint: disable=import-error,invalid-name,broad-except,superfluous-parens
from pyrevit import script
from pyrevit import revit, DB

output = script.get_output()

slopes = {}

for roof in revit.query.get_elements_by_categories(
        [DB.BuiltInCategory.OST_Roofs]
        ):
    for roof_profile in roof.GetProfiles():
        for curve in roof_profile:
            if roof.DefinesSlope[curve]:
                slope_value = revit.units.format_slope(roof.SlopeAngle[curve])
                if slope_value in slopes.keys():
                    slopes[slope_value].append(roof.Id)
                else:
                    slopes[slope_value] = [roof.Id]

for sl, elids in slopes.items():
    print('SLOPE: {0}'.format(sl))
    print('ROOF ELEMENTS WITH THIS SLOPE:')
    element_links = ''
    for elid in elids:
        element_links += output.linkify(elid)
    print(element_links)
    print('\n')
