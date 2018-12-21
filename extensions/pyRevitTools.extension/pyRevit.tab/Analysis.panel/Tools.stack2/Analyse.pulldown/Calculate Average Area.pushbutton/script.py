#pylint: disable=E0401,C0103
from pyrevit import revit, DB
from pyrevit import script


output = script.get_output()


__context__ = 'selection'
__doc__ = 'Find all Rooms/Areas/Spaces with identical names to the select '\
          'room, area or space and calculates the average area '\
          'of that space type.'


areas = DB.FilteredElementCollector(revit.doc)\
          .OfCategory(DB.BuiltInCategory.OST_Areas)\
          .WhereElementIsNotElementType().ToElements()

rms = DB.FilteredElementCollector(revit.doc)\
        .OfCategory(DB.BuiltInCategory.OST_Rooms)\
        .WhereElementIsNotElementType().ToElements()

spaces = DB.FilteredElementCollector(revit.doc)\
           .OfCategory(DB.BuiltInCategory.OST_MEPSpaces)\
           .WhereElementIsNotElementType().ToElements()


processed_items = {DB.Area: [],
                   DB.Architecture.Room: [],
                   DB.Mechanical.Space: []}


selection = revit.get_selection()


for el in selection.elements:
    count = 0
    total = 0.0
    average = 0.0
    if isinstance(el, DB.Area):
        selareaname = el.Parameter[DB.BuiltInParameter.ROOM_NAME].AsString()
        if selareaname not in processed_items[DB.Area]:
            print("AREA TYPE IS: {}".format(selareaname))
            for area in areas:
                areaname = \
                    area.Parameter[DB.BuiltInParameter.ROOM_NAME].AsString()
                if area.AreaScheme.Name == el.AreaScheme.Name\
                        and selareaname == areaname:
                    area_param = area.Parameter[DB.BuiltInParameter.ROOM_AREA]
                    area_val = area_param.AsDouble()
                    print('+ Area \"{}\" = {}'.format(
                        output.linkify(area.Id),
                        areaname,
                        revit.units.format_area(area_val)
                        ))
                    total += area_val
                    count += 1
            print("TOTAL OF {} AREAS WERE FOUND.".format(count))
            processed_items[DB.Area].append(selareaname)
    elif isinstance(el, DB.Architecture.Room):
        selroomname = el.Parameter[DB.BuiltInParameter.ROOM_NAME].AsString()
        if selroomname not in processed_items[DB.Architecture.Room]:
            print("ROOM TYPE IS: {}".format(selroomname))
            for room in rms:
                roomname = \
                    room.Parameter[DB.BuiltInParameter.ROOM_NAME].AsString()
                if selroomname == roomname:
                    area_param = room.Parameter[DB.BuiltInParameter.ROOM_AREA]
                    area_val = area_param.AsDouble()
                    print('{} Room \"{}\" = {}'.format(
                        output.linkify(room.Id),
                        roomname,
                        revit.units.format_area(area_val)
                        ))
                    total += area_val
                    count += 1
            print("TOTAL OF {} ROOMS WERE FOUND.".format(count))
            processed_items[DB.Architecture.Room].append(selroomname)
    elif isinstance(el, DB.Mechanical.Space):
        selspacename = el.Parameter[DB.BuiltInParameter.ROOM_NAME].AsString()
        if selspacename not in processed_items[DB.Mechanical.Space]:
            print("SPACE TYPE IS: {}".format(selspacename))
            for space in spaces:
                spacename = \
                    space.Parameter[DB.BuiltInParameter.ROOM_NAME].AsString()
                if selspacename == spacename:
                    area_param = space.Parameter[DB.BuiltInParameter.ROOM_AREA]
                    area_val = area_param.AsDouble()
                    print('{} Space \"{}\" = {}'.format(
                        output.linkify(space.Id),
                        spacename,
                        revit.units.format_area(area_val)
                        ))
                    total += area_val
                    count += 1
            print("TOTAL OF {} SPACES WERE FOUND.".format(count))
            processed_items[DB.Mechanical.Space].append(selspacename)

    if count != 0:
        average = total / count
        print('\nAVERAGE AREA OF THE SELECTED TYPE IS:'
              '\n{0}'
              '\n ======================================='
              '\n{1} ACRE'.format(revit.units.format_area(average),
                                  average / 43560))
