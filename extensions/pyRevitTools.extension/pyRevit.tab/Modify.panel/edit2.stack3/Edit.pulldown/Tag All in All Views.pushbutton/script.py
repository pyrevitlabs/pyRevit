"""Tag all chosen element types in all views."""
#pylint: disable=C0103,E0401,C0111
from pyrevit import revit, DB
from pyrevit import script
from pyrevit import forms


logger = script.get_logger()
output = script.get_output()


views = DB.FilteredElementCollector(revit.doc)\
          .OfCategory(DB.BuiltInCategory.OST_Views)\
          .WhereElementIsNotElementType()\
          .ToElements()


def GetElementCenter(el):
    cen = el.Location.Point
    z = (el.UpperLimit.Elevation + el.LimitOffset) / 2
    cen = cen.Add(DB.XYZ(0, 0, z))
    return cen


def tag_all_rooms():
    rooms = DB.FilteredElementCollector(revit.doc)\
              .OfCategory(DB.BuiltInCategory.OST_Rooms)\
              .WhereElementIsNotElementType()\
              .ToElements()

    with revit.Transaction('Tag All Rooms in All Views'):
        for view in views:
            for el in rooms:
                room_center = GetElementCenter(el)
                if not room_center:
                    logger.debug('Can not detect center for element: {}',
                                 output.linkify(el.Id))
                    continue
                if isinstance(view, (DB.ViewSection, DB.ViewPlan)):
                    logger.debug('Working on view: %s',
                                 revit.query.get_name(view))
                    room_tag = \
                        revit.doc.Create.NewRoomTag(
                            DB.LinkElementId(el.Id),
                            DB.UV(room_center.X, room_center.Y),
                            view.Id
                            )
                    if isinstance(view, DB.ViewSection):
                        room_tag.Location.Move(DB.XYZ(0, 0, room_center.Z))


def tag_all_spaces():
    spaces = DB.FilteredElementCollector(revit.doc)\
               .OfCategory(DB.BuiltInCategory.OST_MEPSpaces)\
               .WhereElementIsNotElementType()\
               .ToElements()

    with revit.Transaction('Tag All Spaces in All Views'):
        for view in views:
            for el in spaces:
                space_center = GetElementCenter(el)
                if not space_center:
                    logger.debug('Can not detect center for element: {}',
                                 output.linkify(el.Id))
                    continue
                if isinstance(view, (DB.ViewSection, DB.ViewPlan)):
                    logger.debug('Working on view: %s',
                                 revit.query.get_name(view))
                    space_tag = \
                        revit.doc.Create.NewRoomTag(
                            DB.LinkElementId(el.Id),
                            DB.UV(space_center.X, space_center.Y),
                            view.Id
                            )
                    if isinstance(view, DB.ViewSection):
                        space_tag.Location.Move(DB.XYZ(0, 0, space_center.Z))


options_dict = {'Tag All Rooms in All Views': tag_all_rooms,
                'Tag All Spaces in All Views': tag_all_spaces}

selected_switch = \
    forms.CommandSwitchWindow.show(options_dict.keys())

option_func = options_dict.get(selected_switch, None)

if option_func:
    option_func()
