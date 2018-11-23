from pyrevit import revit, DB


__doc__ = 'Sometimes when a revision cloud is placed inside a view '\
          '(instead of a sheet) and the view is placed on a sheet, '\
          'the revision schedule on the sheet does not get updated '\
          'with the revision number of the cloud inside the sheeted view. '\
          'This script verifies that the sheet revision schedule is '\
          'actually listing all the revisions shown inside '\
          'the views of that sheet.'


# Collecting all revisions
revclouds = DB.FilteredElementCollector(revit.doc)\
              .OfCategory(DB.BuiltInCategory.OST_RevisionClouds)\
              .WhereElementIsNotElementType()

# Collecting all sheets
shts = DB.FilteredElementCollector(revit.doc)\
         .OfCategory(DB.BuiltInCategory.OST_Sheets)\
         .WhereElementIsNotElementType()\
         .ToElements()

sheets = sorted(shts, key=lambda x: x.SheetNumber)

# make a dictionary of all viewports on each sheet
sheetvpdict = {sh.Id.IntegerValue: [revit.doc.GetElement(x).ViewId
                                    for x in sh.GetAllViewports()]
               for sh in sheets}

# make a dictionary of all revisions and the associated sheets
sheetrevs = {sh.Id.IntegerValue: [] for sh in sheets}

atleastonecrazysheetwasfound = False

print('SEARCHING...\n')

for revcloud in revclouds:
    # get revision info
    revid = revcloud.RevisionId.IntegerValue

    # get parent view
    parentvpid = revcloud.OwnerViewId
    parentvp = revit.doc.GetElement(parentvpid)

    if isinstance(parentvp, DB.ViewSheet):
        continue    # nevermind if parent view is a sheet
    else:
        # find the sheets showing the parent view
        for sheetid in sheetvpdict:
            if parentvpid in sheetvpdict:
                # add the revision to the list of revisions
                # that should be on sheet
                sheetrevs[sheetid].append(revid)

# after the above loop the revsheets dictionary should be complete
for sheetid, revids in sheetrevs.items():
    missedrevids = []
    sheet = revit.doc.GetElement(DB.ElementId(sheetid))
    listedrevids = [x.IntegerValue for x in sheet.GetAllRevisionIds()]
    for revid in revids:
        if revid not in listedrevids:
            missedrevids.append(revid)
            atleastonecrazysheetwasfound = True
    if len(missedrevids) > 0:
        print('SHEET:  {0}\t{1}\nDOES NOT LIST THESE REVISIONS:\n'
              .format(sheet.Parameter[DB.BuiltInParameter.SHEET_NUMBER].AsString(),
                      sheet.Parameter[DB.BuiltInParameter.SHEET_NAME].AsString()))

        for revid in missedrevids:
            if revid not in listedrevids:
                rev = revit.doc.GetElement(DB.ElementId(revid))
                revit.report.print_revision(rev, prefix='\t', print_id=False)

if atleastonecrazysheetwasfound:
    print('\nSEARCH COMPLETED.')
else:
    print('SEARCH COMPLETED.\nALL REVISION SCHEDULES ARE CORRECT.')
