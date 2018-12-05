"""Finds and lists rooms with identical numbers."""

import collections

from pyrevit import revit, DB

curview = revit.activeview

rooms = DB.FilteredElementCollector(revit.doc, curview.Id)\
          .OfCategory(DB.BuiltInCategory.OST_Rooms)\
          .WhereElementIsNotElementType()\
          .ToElementIds()

roomnums = [revit.doc.GetElement(rmid).Number for rmid in rooms]
duplicates = [item
              for item, count in collections.Counter(roomnums).items()
              if count > 1]

if len(duplicates) > 0:
    for rn in duplicates:
        print('IDENTICAL ROOM NUMBER:  {}'.format(rn))
        for rmid in rooms:
            rm = revit.doc.GetElement(rmid)
            if rm.Number == rn:
                print('\tROOM NAME:  {} LEVEL: {}'
                      .format(rm.LookupParameter('Name').AsString().ljust(30),
                              rm.Level.Name))
        print('\n')
else:
    print('No identical room numbers were found.')
