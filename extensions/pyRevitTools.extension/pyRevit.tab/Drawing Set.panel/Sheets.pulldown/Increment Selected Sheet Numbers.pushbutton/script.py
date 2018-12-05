from pyrevit import coreutils
from pyrevit import revit, DB
from pyrevit import forms
from pyrevit import script, revit


__doc__ = 'Increases the sheet number of the selected sheets by one. '\
          'The sheet name change will be printed if logging is set '\
          'to Verbose in pyRevit settings.'


logger = script.get_logger()

selection = revit.get_selection()


shift = 1

selected_sheets = forms.select_sheets(title='Select Sheets')
if not selected_sheets:
    script.exit()

sorted_sheet_list = sorted(selected_sheets, key=lambda x: x.SheetNumber)
if shift >= 0:
    sorted_sheet_list.reverse()
with DB.TransactionGroup(revit.doc, 'Shift Sheets') as tgr:
    tgr.Start()
    for sheet in sorted_sheet_list:
        with DB.Transaction(revit.doc, 'Shift Single Sheet') as t:
            t.Start()
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
            t.Commit()
    tgr.Assimilate()