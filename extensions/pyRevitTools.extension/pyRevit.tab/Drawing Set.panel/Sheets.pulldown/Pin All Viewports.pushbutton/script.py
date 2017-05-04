"""Pins all viewports on selected sheets or active sheet"""

import sys
from revitutils import selection, doc, uidoc, curview, Action
from Autodesk.Revit.UI import TaskDialog
from Autodesk.Revit.DB import ViewSheet



filteredlist = []
sheetlist = []

if selection.is_empty:
    if isinstance(curview, ViewSheet):
        sheetlist.append(curview)
else:
    for sel_view in selection:
        if isinstance(sel_view, ViewSheet):
            sheetlist.append(sel_view)

if not sheetlist:
    TaskDialog.Show('pyrevit','You must have at least one sheet selected or active view must be a sheet.')
    sys.exit()

with Action('Pin all viewports'):
    for sheet in sheetlist:
        count = 0
        alreadypinnedcount = 0
        for vportid in sheet.GetAllViewports():
            vport = doc.GetElement(vportid)
            if not vport.Pinned:
                vport.Pinned = True
                count += 1
            else:
                alreadypinnedcount += 1
        print('Pinned {} viewports on sheet: {} - {}'
              '\n({} viewports were already pinned)'
              .format(count, sheet.SheetNumber, sheet.Name, alreadypinnedcount))
