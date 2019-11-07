"""Get a total count and types of parking elements in the current view."""

from pyrevit.framework import List
from pyrevit import revit, DB


parkings = DB.FilteredElementCollector(revit.doc, revit.active_view.Id)\
             .OfCategory(DB.BuiltInCategory.OST_Parking)\
             .WhereElementIsNotElementType()\
             .ToElementIds()

print('PARKING COUNT: {0}'.format(len(list(parkings))))

ptypesdic = {}

for pid in parkings:
    ptype = revit.doc.GetElement(revit.doc.GetElement(pid).GetTypeId())
    ptname = revit.query.get_name(ptype)
    if ptname in ptypesdic:
        ptypesdic[ptname] += 1
    else:
        ptypesdic[ptname] = 1

print('PARKING TYPES AND COUNTS')
for ptname, ptcount in ptypesdic.items():
    print('TYPE: {0}COUNT: {1}'.format(ptname.ljust(35), ptcount))
