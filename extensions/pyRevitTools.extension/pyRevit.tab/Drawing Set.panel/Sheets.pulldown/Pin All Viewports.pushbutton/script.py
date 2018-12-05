"""Pins all viewports on selected sheets.

Shift-Click:
Pin all viewports on active sheet.
"""

import sys

from pyrevit import revit, DB, UI
from pyrevit import script
from pyrevit import forms


def pin_viewports(sheet_list):
    with revit.Transaction('Pin all viewports'):
        for sheet in sheet_list:
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


if __shiftclick__:
    if isinstance(revit.activeview, DB.ViewSheet):
        sel_sheets = [revit.activeview]
    else:
        forms.alert('Active view must be a sheet.')
        script.exit()
else:
    sel_sheets = forms.select_sheets(title='Select Sheets')


if sel_sheets:
    pin_viewports(sel_sheets)
