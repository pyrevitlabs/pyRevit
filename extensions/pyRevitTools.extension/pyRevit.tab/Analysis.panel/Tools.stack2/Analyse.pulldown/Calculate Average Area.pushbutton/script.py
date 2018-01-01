from pyrevit import revit, DB


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
        selareaname = el.LookupParameter('Name').AsString()
        if selareaname not in processed_items[DB.Area]:
            print("AREA TYPE IS: {}".format(selareaname))
            for area in areas:
                areaname = area.LookupParameter('Name').AsString()
                if area.AreaScheme.Name == el.AreaScheme.Name\
                        and selareaname == areaname:
                    total += area.LookupParameter('Area').AsDouble()
                    count += 1
            print("TOTAL OF {} AREAS WERE FOUND.".format(count))
            processed_items[DB.Area].append(selareaname)
    elif isinstance(el, DB.Architecture.Room):
        selroomname = el.LookupParameter('Name').AsString()
        if selroomname not in processed_items[DB.Architecture.Room]:
            print("ROOM TYPE IS: {}".format(selroomname))
            for room in rms:
                roomname = room.LookupParameter('Name').AsString()
                if selroomname == roomname:
                    total += room.LookupParameter('Area').AsDouble()
                    count += 1
            print("TOTAL OF {} ROOMS WERE FOUND.".format(count))
            processed_items[DB.Architecture.Room].append(selroomname)
    elif isinstance(el, DB.Mechanical.Space):
        selspacename = el.LookupParameter('Name').AsString()
        if selspacename not in processed_items[DB.Mechanical.Space]:
            print("SPACE TYPE IS: {}".format(selspacename))
            for space in spaces:
                spacename = space.LookupParameter('Name').AsString()
                if selspacename == spacename:
                    total += space.LookupParameter('Area').AsDouble()
                    count += 1
            print("TOTAL OF {} SPACES WERE FOUND.".format(count))
            processed_items[DB.Mechanical.Space].append(selspacename)

    if count != 0:
        average = total / count
        print('AVERAGE AREA OF THE SELECTED TYPE IS:'
              '\n{0} SQFT'
              '\n{1} ACRE'.format(average, average / 43560))
