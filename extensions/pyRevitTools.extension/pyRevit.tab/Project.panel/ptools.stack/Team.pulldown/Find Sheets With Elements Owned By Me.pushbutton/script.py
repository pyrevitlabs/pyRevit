from pyrevit import HOST_APP
from pyrevit import revit, DB, UI
from pyrevit import forms


__doc__ = 'Lists all sheets containing elements currently "owned" '\
          'by the user. "Owned" elements are the elements' \
          'by the user since the last synchronize and release.'


sheetsnotsorted = DB.FilteredElementCollector(revit.doc)\
                    .OfCategory(DB.BuiltInCategory.OST_Sheets)\
                    .WhereElementIsNotElementType()\
                    .ToElements()

sheets = sorted(sheetsnotsorted, key=lambda x: x.SheetNumber)

filteredlist = []

if revit.doc.IsWorkshared:
    print('Searching all sheets...\n')
    print('NAME      NUMBER')
    print('-'*100)
    for sheet in sheets:
        sheetisedited = False
        sheetviewlist = []
        sheetviewlist.append(sheet.Id)
        vportids = sheet.GetAllViewports()
        for vportid in vportids:
            sheetviewlist.append(revit.doc.GetElement(vportid).ViewId)
        for view in sheetviewlist:
            curviewelements = DB.FilteredElementCollector(revit.doc)\
                                .OwnedByView(view)\
                                .WhereElementIsNotElementType()\
                                .ToElements()

            if len(curviewelements) > 0:
                for el in curviewelements:
                    wti = DB.WorksharingUtils.GetWorksharingTooltipInfo(
                        revit.doc,
                        el.Id
                        )
                    # wti.Creator, wti.Owner, wti.LastChangedBy
                    if wti.Owner == HOST_APP.username:
                        filteredlist.append(sheet)
                        print('{0}{1}'
                              .format(
                                  sheet.Parameter[DB.BuiltInParameter.SHEET_NUMBER]
                                       .AsString().ljust(10),
                                  sheet.Parameter[DB.BuiltInParameter.SHEET_NAME]
                                       .AsString().ljust(50)
                                       )
                              )

                        sheetisedited = True
                        break
            if sheetisedited:
                break
        else:
            pass
    print('\nAll done...')
else:
    forms.alert('Model is not workshared.')
