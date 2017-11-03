from pyrevit import coreutils
from pyrevit import revit, DB
from pyrevit import script


__doc__ = 'Increases the sheet number of the selected sheets by one. '\
          'The sheet name change will be printed if logging is set '\
          'to Verbose in pyRevit settings.'


logger = script.get_logger()

selection = revit.get_selection()


shift = 1

selected_sheets = []
for sheet in selection.elements:
    if isinstance(sheet, DB.ViewSheet):
        selected_sheets.append(sheet)

sorted_sheet_list = sorted(selected_sheets, key=lambda x: x.SheetNumber)

if shift >= 0:
    sorted_sheet_list.reverse()

with revit.Transaction('Shift Sheets'):
    for sheet in sorted_sheet_list:
        try:
            cur_sheet_num = sheet.SheetNumber
            sheet_num_param = sheet.LookupParameter('Sheet Number')
            sheet_num_param.Set(coreutils.increment_str(sheet.SheetNumber,
                                                        shift))
            new_sheet_num = sheet.SheetNumber
            logger.info('{} -> {}'.format(cur_sheet_num, new_sheet_num))
        except Exception as shift_err:
            logger.error(shift_err)

    revit.doc.Regenerate()
