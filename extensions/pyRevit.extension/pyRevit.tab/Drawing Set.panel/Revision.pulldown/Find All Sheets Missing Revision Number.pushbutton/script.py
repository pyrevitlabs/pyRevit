"""
Copyright (c) 2014-2016 Ehsan Iran-Nejad
Python scripts for Autodesk Revit

This file is part of pyRevit repository at https://github.com/eirannejad/pyRevit

pyRevit is a free set of scripts for Autodesk Revit: you can redistribute it and/or modify
it under the terms of the GNU General Public License version 3, as published by
the Free Software Foundation.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

See this link for a copy of the GNU General Public License protecting this package.
https://github.com/eirannejad/pyRevit/blob/master/LICENSE
"""

__doc__ =   'Sometimes when a revision cloud is placed inside a view (instead of a sheet) and the view is' \
            ' placed on a sheet, the revision schedule on the sheet does not get updated with the revision' \
            ' number of the cloud inside the sheeted view. This script verifies that the sheet revision' \
            ' schedule is actually listing all the revisions shown inside the views of that sheet.'

from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory, ViewSheet, ElementId

doc = __revit__.ActiveUIDocument.Document

# Collecting all revisions
cl = FilteredElementCollector(doc)
revclouds = cl.OfCategory(BuiltInCategory.OST_RevisionClouds).WhereElementIsNotElementType()
# Collecting all sheets
cl_views = FilteredElementCollector(doc)
shts = cl_views.OfCategory(BuiltInCategory.OST_Sheets).WhereElementIsNotElementType().ToElements()
sheets = sorted(shts, key=lambda x: x.SheetNumber)
# make a dictionary of all viewports on each sheet
sheetvpdict = { sh.Id.IntegerValue:[doc.GetElement(x).ViewId for x in sh.GetAllViewports()] for sh in sheets}
# make a dictionary of all revisions and the associated sheets
sheetrevs = {sh.Id.IntegerValue:[] for sh in sheets}

atleastonecrazysheetwasfound = False

print('SEARCHING...\n')

for revcloud in revclouds:
    # get revision info
    revid = revcloud.RevisionId.IntegerValue
    revnum = doc.GetElement(ElementId(revid)).RevisionNumber
    
    # get parent view
    parentvpid = revcloud.OwnerViewId
    parentvp = doc.GetElement(parentvpid)
    
    if isinstance(parentvp, ViewSheet):
        continue    # nevermind if parent view is a sheet
    else:
        for sheetid in sheetvpdict:                 # find the sheets showing the parent view
            if parentvpid in sheetvpdict:
                sheetrevs[sheetid].append(revid)    # add the revision to the list of revisions that should be on sheet

# after the above loop the revsheets dictionary should be complete
for sheetid, revids in sheetrevs.items():
    missedrevids = []
    sheet = doc.GetElement(ElementId(sheetid))
    listedrevids = [x.IntegerValue for x in sheet.GetAllRevisionIds()]
    for revid in revids:
        if revid not in listedrevids:
            missedrevids.append(revid)
            atleastonecrazysheetwasfound = True
    if len(missedrevids) > 0:
        print('SHEET:  {0}\t{1}\nDOES NOT LIST THESE REVISIONS:\n'.format(sheet.LookupParameter('Sheet Number').AsString(),
                                                                           sheet.LookupParameter('Sheet Name').AsString()
                                                                           ))
        for revid in missedrevids:
            if revid not in listedrevids:
                rev = doc.GetElement(ElementId(revid))            
                print('\tREV#: {0}\t\tDATE: {1}\t\tDESC:{2}'.format(rev.RevisionNumber,
                                                                    rev.RevisionDate,
                                                                    rev.Description
                                                                    ))
if atleastonecrazysheetwasfound:
    print('\nSEARCH COMPLETED.')
else:
    print('SEARCH COMPLETED.\nALL REVISION SCHEDULES ARE CORRECT.')
