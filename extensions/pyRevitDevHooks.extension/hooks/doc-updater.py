from pyrevit import EXEC_PARAMS
from pyrevit import revit, DB

doc = EXEC_PARAMS.event_doc

for wall in revit.query.get_elements_by_class(DB.Wall, doc=doc):
    p = wall.get_Parameter(DB.BuiltInParameter.WALL_USER_HEIGHT_PARAM)
    print("wall: {} Unconnected Height: {}".format(str(wall.Id), p.AsDouble()))
