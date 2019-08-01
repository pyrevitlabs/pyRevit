"""Finds and lists rooms with identical numbers."""
#pylint: disable=invalid-name,import-error,superfluous-parens
from collections import Counter

from pyrevit import revit, DB
from pyrevit import script

output = script.get_output()

if revit.active_view:
    rooms = DB.FilteredElementCollector(revit.doc, revit.active_view.Id)\
            .OfCategory(DB.BuiltInCategory.OST_Rooms)\
            .WhereElementIsNotElementType()\
            .ToElementIds()

    room_numbers = [revit.doc.GetElement(room_id).Number for room_id in rooms]
    duplicates = \
        [item for item, count in Counter(room_numbers).items() if count > 1]

    if duplicates:
        for room_number in duplicates:
            print('IDENTICAL ROOM NUMBER:  {}'.format(room_number))
            for room_id in rooms:
                rm = revit.doc.GetElement(room_id)
                if rm.Number == room_number:
                    room_name = \
                        rm.Parameter[DB.BuiltInParameter.ROOM_NAME].AsString()
                    print('\t{} (@ {}) {}'.format(room_name.ljust(30),
                                                  rm.Level.Name,
                                                  output.linkify(rm.Id)))
            print('\n')
    else:
        print('No identical room numbers were found.')
