"""Pins all viewports on selected sheets or active sheet."""

import sys

from pyrevit import revit, DB, UI


selection = revit.get_selection()
curview = revit.activeview


filteredlist = []
sheetlist = []

if selection.is_empty:
    if isinstance(curview, DB.ViewSheet):
        sheetlist.append(curview)
else:
    for sel_view in selection:
        if isinstance(sel_view, DB.ViewSheet):
            sheetlist.append(sel_view)

if not sheetlist:
    UI.TaskDialog.Show('pyrevit',
                       'You must have at least one sheet selected '
                       'or active view must be a sheet.')
    sys.exit()

with revit.Transaction('Pin all viewports'):
    for sheet in sheetlist:
        count = 0
        alreadypinnedcount = 0
        for vportid in sheet.GetAllViewports():
            vport = revit.doc.GetElement(vportid)
            if not vport.Pinned:
                vport.Pinned = True
                count += 1
            else:
                alreadypinnedcount += 1
        print('Pinned {} viewports on sheet: {} - {}'
              '\n({} viewports were already pinned)'
              .format(count,
                      sheet.SheetNumber,
                      sheet.Name,
                      alreadypinnedcount))
