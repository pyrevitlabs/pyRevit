"""Manage sheet packages."""
#pylint: disable=C0111,E0401,C0103,W0613,W0703
from pyrevit import revit, DB
from pyrevit import forms
from pyrevit import script


logger = script.get_logger()
output = script.get_output()


class SheetDataGridItem(object):
    def __init__(self, view_sheet):
        self._item = view_sheet
        self.name = self._item.Name
        self.number = self._item.SheetNumber
        self.printable = self._item.CanBePrinted
        self.order_index = 0

    @property
    def revit_item(self):
        return self._item


class ManagePackagesWindow(forms.WPFWindow):
    def __init__(self, xaml_file_name):
        forms.WPFWindow.__init__(self, xaml_file_name)

        # get all sheets
        sheets = revit.query.get_sheets(include_noappear=False)
        sheet_dg = [SheetDataGridItem(x) for x in sheets]

        # scroll to last column for convenience
        self.sheets_dg.ItemsSource = sheet_dg
        last_col = list(self.sheets_dg.Columns)[-1]
        self.sheets_dg.ScrollIntoView(sheet_dg[0], last_col)

    def update_sheets(self, sender, args):
        self.Close()



ManagePackagesWindow('ManagePackagesWindow.xaml').ShowDialog()
