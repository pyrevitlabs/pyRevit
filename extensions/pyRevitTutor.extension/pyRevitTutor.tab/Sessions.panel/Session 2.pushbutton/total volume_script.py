"""Calculates total volume of all walls in the model."""

__title__ = 'Total\nVolume'
__author__ = 'Ehsan Iran-Nejad'


from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory

doc = __revit__.ActiveUIDocument.Document


# Creating collector instance and collecting all the walls from the model
wall_collector = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Walls).WhereElementIsNotElementType()


# Iterate over wall and collect Volume data

total_volume = 0.0

for wall in wall_collector:
    vol_param = wall.LookupParameter('Volume')
    if vol_param:
        total_volume = total_volume + vol_param.AsDouble()

# now that results are collected, print the total
print("Total Volume is: {}".format(total_volume))