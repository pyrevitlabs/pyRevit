import re

from pyrevit import coreutils
from pyrevit import revit, DB
from pyrevit import forms
from pyrevit import script


__helpurl__ = "{{docpath}}SJzs9ZxqRYc"

__doc__ = 'Enter sheet names and numbers in the text box and '\
          'this tool will create all at once.'


logger = script.get_logger()


class BatchSheetMakerWindow(forms.WPFWindow):
    def __init__(self, xaml_file_name):
        forms.WPFWindow.__init__(self, xaml_file_name)
        self._sheet_dict = {}
        self._titleblock_id = None
        self.sheets_tb.Focus()

    def _process_sheet_code(self):
        for sheet_code in str(self.sheets_tb.Text).split('\n'):
            if coreutils.is_blank(sheet_code):
                continue

            if '\t' not in sheet_code:
                logger.warning('Sheet name must be separated from '
                               'sheet number by a single tab: {}'
                               .format(sheet_code))
                return False

            sheet_code = re.sub('\t+', '\t', sheet_code)
            sheet_code = sheet_code.replace('\n', '').replace('\r', '')
            num, name = sheet_code.split('\t')
            try:
                for range_num in coreutils.extract_range(num):
                    self._sheet_dict[range_num] = name
            except Exception as range_err:
                logger.error(range_err)
                return False

        return True

    def _ask_for_titleblock(self):
        tblock = forms.select_titleblocks(doc=revit.doc)
        if tblock is not None:
            self._titleblock_id = tblock
            return True

        return False

    @staticmethod
    def _create_placeholder(sheet_num, sheet_name):
        with DB.Transaction(revit.doc, 'Create Placeholder') as t:
            try:
                t.Start()
                new_phsheet = DB.ViewSheet.CreatePlaceholder(revit.doc)
                new_phsheet.Name = sheet_name
                new_phsheet.SheetNumber = sheet_num
                t.Commit()
            except Exception as create_err:
                t.RollBack()
                logger.error('Error creating placeholder sheet {}:{} | {}'
                             .format(sheet_num, sheet_name, create_err))

    def _create_sheet(self, sheet_num, sheet_name):
        with DB.Transaction(revit.doc, 'Create Sheet') as t:
            try:
                t.Start()
                new_phsheet = DB.ViewSheet.Create(revit.doc,
                                                  self._titleblock_id)
                new_phsheet.Name = sheet_name
                new_phsheet.SheetNumber = sheet_num
                t.Commit()
            except Exception as create_err:
                t.RollBack()
                logger.error('Error creating sheet sheet {}:{} | {}'
                             .format(sheet_num, sheet_name, create_err))

    def create_sheets(self, sender, args):
        self.Close()

        if self._process_sheet_code():
            if self.sheet_cb.IsChecked:
                create_func = self._create_sheet
                transaction_msg = 'Batch Create Sheets'
                if not self._ask_for_titleblock():
                    script.exit()
            else:
                create_func = self._create_placeholder
                transaction_msg = 'Batch Create Placeholders'

            with DB.TransactionGroup(revit.doc, transaction_msg) as tg:
                tg.Start()
                for sheet_num, sheet_name in self._sheet_dict.items():
                    logger.debug('Creating Sheet: {}:{}'.format(sheet_num,
                                                                sheet_name))
                    create_func(sheet_num, sheet_name)
                tg.Assimilate()
        else:
            logger.error('Aborted with errors.')


BatchSheetMakerWindow('BatchSheetMakerWindow.xaml').ShowDialog()
