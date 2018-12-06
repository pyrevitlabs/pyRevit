from pyrevit import revit, DB


__doc__ = 'Find all sheets referencing the current view.'\
          ' Especially useful for finding legends.'


cl_views = DB.FilteredElementCollector(revit.doc)
shts = cl_views.OfCategory(DB.BuiltInCategory.OST_Sheets)\
               .WhereElementIsNotElementType()\
               .ToElements()

sheets = sorted(shts, key=lambda x: x.SheetNumber)

curview = revit.activeview
count = 0

print('Searching All Sheets for {0} ID:{1}\n'.format(curview.Name, curview.Id))
for s in sheets:
    vpsIds = [revit.doc.GetElement(x).ViewId for x in s.GetAllViewports()]
    curviewelements = DB.FilteredElementCollector(revit.doc)\
                        .OwnedByView(s.Id)\
                        .WhereElementIsNotElementType()\
                        .ToElements()

    for el in curviewelements:
        if isinstance(el, DB.ScheduleSheetInstance):
            vpsIds.append(el.ScheduleId)

    if curview.Id in vpsIds:
        count += 1
        print('NUMBER: {0}   NAME:{1}'
              .format(s.Parameter[DB.BuiltInParameter.SHEET_NUMBER].AsString().rjust(10),
                      s.Parameter[DB.BuiltInParameter.SHEET_NAME].AsString().ljust(50)))

print('\n\nView is referenced on {0} sheets.'.format(count))
