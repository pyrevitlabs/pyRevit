"""Advanced Collection of Data: Collects all the walls of height 10"""


# for timing -------------------------------------------------------------------
from pyrevit.coreutils import Timer
timer = Timer()
# ------------------------------------------------------------------------------


import Autodesk.Revit.DB as DB


doc = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument

height_param_id = DB.ElementId(DB.BuiltInParameter.WALL_USER_HEIGHT_PARAM)

height_param_prov = DB.ParameterValueProvider(height_param_id)

param_equality = DB.FilterNumericEquals()

heigh_value_rule = DB.FilterDoubleRule(height_param_prov,
                                       param_equality,
                                       10.0,
                                       1E-6)

param_filter = DB.ElementParameterFilter(heigh_value_rule)


walls = DB.FilteredElementCollector(doc) \
          .WherePasses(param_filter) \
          .ToElementIds()


uidoc.Selection.SetElementIds(walls)



# for timing -------------------------------------------------------------------
endtime = timer.get_time()
print(endtime)
# ------------------------------------------------------------------------------
