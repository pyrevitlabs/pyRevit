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

rooms = DB.FilteredElementCollector(revit.doc)\
          .OfCategory(DB.BuiltInCategory.OST_Rooms)\
          .WhereElementIsNotElementType().ToElements()

spaces = DB.FilteredElementCollector(revit.doc)\
           .OfCategory(DB.BuiltInCategory.OST_MEPSpaces)\
           .WhereElementIsNotElementType().ToElements()


processed_items = {DB.Area: [],
                   DB.Architecture.Room: [],
                   DB.Mechanical.Space: []}


selection = revit.get_selection()


def calc_and_print(items, item_type, type_name, match_name):
    item_total_area = 0.0
    item_count = 0
    if match_name not in processed_items[item_type]:
        print("{} TYPE IS: {}".format(type_name, match_name))
        for item in items:
            item_name = \
                item.Parameter[DB.BuiltInParameter.ROOM_NAME].AsString()
            item_number = \
                item.Parameter[DB.BuiltInParameter.ROOM_NUMBER].AsString()
            item_level = \
                item.Parameter[
                    DB.BuiltInParameter.ROOM_LEVEL_ID].AsValueString()
            if revit.query.is_placed(item):
                if match_name == item_name:
                    area_value = \
                        item.Parameter[DB.BuiltInParameter.ROOM_AREA].AsDouble()
                    print('{} {} #{} \"{}\" @ \"{}\" = {}'.format(
                        output.linkify(item.Id),
                        type_name.title(),
                        item_number,
                        item_name,
                        item_level,
                        revit.units.format_area(area_value)
                        ))
                    item_total_area += area_value
                    item_count += 1
            else:
                print(':cross_mark: '
                      'SKIPPED \"NOT PLACED\" {} {} #{} \"{}\" @ \"{}\"'
                      .format(
                          output.linkify(item.Id),
                          type_name.title(),
                          item_number,
                          item_name,
                          item_level))
        print("TOTAL OF {} {}S WERE FOUND.".format(item_count, type_name))
        processed_items[item_type].append(match_name)
    return item_total_area, item_count


for el in selection.elements:
    count = 0
    total = 0.0
    if isinstance(el, DB.Area):
        target_name = el.Parameter[DB.BuiltInParameter.ROOM_NAME].AsString()
        area_total, area_count = \
            calc_and_print(areas, DB.Area, 'AREA', target_name)
        count += area_count
        total += area_total
    elif isinstance(el, DB.Architecture.Room):
        target_name = el.Parameter[DB.BuiltInParameter.ROOM_NAME].AsString()
        area_total, area_count = \
            calc_and_print(rooms, DB.Architecture.Room, 'ROOM', target_name)
        count += area_count
        total += area_total
    elif isinstance(el, DB.Mechanical.Space):
        target_name = el.Parameter[DB.BuiltInParameter.ROOM_NAME].AsString()
        area_total, area_count = \
            calc_and_print(spaces, DB.Mechanical.Space, 'SPACE', target_name)
        count += area_count
        total += area_total

    if count != 0:
        average = total / count
        print('\nAVERAGE AREA OF THE SELECTED TYPE IS:'
              '\n{}'
              '\n ======================================='
              '\n{} ACRE'
              '\n{} HECTARES'.format(revit.units.format_area(average),
                                     average / 43560,
                                     average / 107639))
