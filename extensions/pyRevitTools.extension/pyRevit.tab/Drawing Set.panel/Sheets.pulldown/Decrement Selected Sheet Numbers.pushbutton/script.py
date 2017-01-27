"""Decreases the sheet number of the selected sheets by one."""

from scriptutils import logger, coreutils
from revitutils import doc, uidoc, selection

from Autodesk.Revit.DB import Transaction, ViewSheet


shift = -1

selected_sheets = []
for sheet in selection.elements:
    if isinstance(sheet, ViewSheet):
        selected_sheets.append(sheet)

sorted_sheet_list = sorted(selected_sheets)

if shift >= 0:
    sorted_sheet_list.reverse()

with Transaction(doc, 'Shift Sheets') as t:
    t.Start()

    for sheet in sorted_sheet_list:
        try:
            cur_sheet_num = sheet.SheetNumber
            sheet_num_param = sheet.LookupParameter('Sheet Number')
            sheet_num_param.Set(coreutils.decrement_str(sheet.SheetNumber, shift))
            new_sheet_num = sheet.SheetNumber
            logger.info('{} -> {}'.format(cur_sheet_num, new_sheet_num))
        except Exception as shift_err:
            logger.error(shift_err)

    doc.Regenerate()
    t.Commit()
