"""Print sheets in order from a sheet index."""
#pylint: disable=W0613,E0401
from pyrevit import framework
from pyrevit.framework import Windows, Drawing
from pyrevit import coreutils
from pyrevit import forms
from pyrevit import revit, DB
from pyrevit import script


logger = script.get_logger()


class ViewSheetListItem(object):
    def __init__(self, view_sheet):
        self._sheet = view_sheet
        self.name = self._sheet.Name
        self.number = self._sheet.SheetNumber
        self.printable = self._sheet.CanBePrinted
        self.order_index = 0

    @property
    def revit_sheet(self):
        return self._sheet


class ReOrderWindow(forms.WPFWindow):
    def __init__(self, xaml_file_name):
        forms.WPFWindow.__init__(self, xaml_file_name)

        self._setup_sheet_params_combobox()

    @property
    def sheet_list(self):
        return self.sheets_lb.ItemsSource

    @sheet_list.setter
    def sheet_list(self, value):
        self.sheets_lb.ItemsSource = value

    @property
    def selected_sheet_param(self):
        return self.orderparams_cb.SelectedItem

    def _update_order_indices(self, sheet_list):
        for idx, sheet in enumerate(sheet_list):
            sheet.order_index = idx

    def _setup_sheet_params_combobox(self):
        sheets = revit.query.get_sheets()
        if sheets:
            sheet_sample = sheets[0]
            sheet_params = [x.Definition.Name for x in sheet_sample.Parameters
                            if x.StorageType == DB.StorageType.Integer
                            or x.StorageType == DB.StorageType.Double]
            self.orderparams_cb.ItemsSource = sorted(sheet_params)
            self.orderparams_cb.ItemsSource.extend(
                ['Sheet Number', 'Sheet Name']
            )
            probable_order_param = None
            for sheet_param in sheet_params:
                if 'order' in sheet_param.lower():
                    probable_order_param = sheet_param
                    break
            if probable_order_param:
                self.orderparams_cb.SelectedItem = probable_order_param
            else:
                self.orderparams_cb.SelectedIndex = 0

    def _get_ordered_sheets(self):
        sheets = revit.query.get_sheets(include_noappear=False)
        if self.selected_sheet_param:
            sheets = sorted(
                sheets,
                key=lambda x: x.LookupParameter(self.selected_sheet_param)
                .AsString()
                )
        return sheets

    def selection_changed(self, sender, args):
        if self.selected_sheet_param:
            sheet_list = [ViewSheetListItem(x)
                          for x in self._get_ordered_sheets()]

            # update oder indices
            self._update_order_indices(sheet_list)
            # Show all sheets
            self.sheet_list = sheet_list

    def reorder_items(self, sender, args):
        pass

    def move_to_top(self, sender, args):
        pass


ReOrderWindow('ReOrderWindow.xaml').ShowDialog()
