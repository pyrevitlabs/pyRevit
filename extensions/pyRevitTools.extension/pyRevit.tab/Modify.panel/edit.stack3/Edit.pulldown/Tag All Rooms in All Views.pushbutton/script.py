from scriptutils import logger
from revitutils import doc, Action

# noinspection PyUnresolvedReferences
from Autodesk.Revit.DB import FilteredElementCollector as Fec
# noinspection PyUnresolvedReferences
from Autodesk.Revit.DB import BuiltInCategory, LinkElementId, UV, XYZ, ViewSection, ViewPlan


views = Fec(doc).OfCategory( BuiltInCategory.OST_Views).WhereElementIsNotElementType().ToElements()
rooms = Fec(doc).OfCategory(BuiltInCategory.OST_Rooms).WhereElementIsNotElementType().ToElements()


def GetElementCenter(el, v):
    cen = el.Location.Point
    z = (el.UpperLimit.Elevation + el.LimitOffset) / 2
    cen = cen.Add( XYZ( 0, 0, z ) )
    return cen


with Action('Tag All Rooms in All Views'):
    for v in views:
        for el in rooms:
            room_center = GetElementCenter(el, v)
            if type(v) in [ViewSection, ViewPlan]:
                logger.debug('Working on view: %s' % v.ViewName)
                roomtag = doc.Create.NewRoomTag(LinkElementId(el.Id), UV(room_center.X, room_center.Y), v.Id)
                if isinstance(v, ViewSection):
                    roomtag.Location.Move(XYZ(0, 0, room_center.Z))
