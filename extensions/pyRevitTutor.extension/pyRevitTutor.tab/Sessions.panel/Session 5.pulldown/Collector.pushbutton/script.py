"""Advanced Collection of Data: Collects all the walls of height 10"""


# for timing -------------------------------------------------------------------
from pyrevit.coreutils import Timer
timer = Timer()
# ------------------------------------------------------------------------------


from System.Collections.Generic import List

import Autodesk.Revit.DB as DB


doc = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument


walls = DB.FilteredElementCollector(doc) \
          .OfCategory(DB.BuiltInCategory.OST_Walls) \
          .WhereElementIsNotElementType() \
          .ToElements()


tallwalls_ids = []

for wall in walls:
    heightp = wall.Parameter[DB.BuiltInParameter.WALL_USER_HEIGHT_PARAM]
    if heightp and heightp.AsDouble() == 10.0:
        tallwalls_ids.append(wall.Id)


uidoc.Selection.SetElementIds(List[DB.ElementId](tallwalls_ids))


# for timing -------------------------------------------------------------------
endtime = timer.get_time()
print(endtime)
# ------------------------------------------------------------------------------
