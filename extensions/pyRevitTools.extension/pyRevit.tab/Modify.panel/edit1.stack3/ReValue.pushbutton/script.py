"""Reformat parameter string values (Super handy for renaming elements)"""
#pylint: disable=E0401
from collections import namedtuple

from pyrevit import coreutils
from pyrevit import revit, DB
from pyrevit import forms
from pyrevit import script

__author__ = "{{author}}"
__context__ = "selection"

logger = script.get_logger()
output = script.get_output()


ReValueItem = namedtuple('ReValueItem', ['oldvalue', 'newvalue'])


class ReValueWindow(forms.WPFWindow):
    def __init__(self, xaml_file_name, rvt_elements=None):
        # create pattern maker window and process options
        forms.WPFWindow.__init__(self, xaml_file_name)
        self._target_elements = revit.get_selection().elements
        self._setup_params()
        # self.orig_format_tb.Text = '{company} - {type} - {name}'
        # self.new_format_tb.Text = 'TVA_{type}_{name}'

    @property
    def selected_param(self):
        return self.params_cb.SelectedItem

    def _setup_params(self):
        unique_params = set()
        for element in self._target_elements:
            for param in element.Parameters:
                if param.StorageType == DB.StorageType.String:
                    unique_params.add(param.Definition.Name)

        all_params = ['Name']
        all_params.extend(sorted(list(unique_params)))
        self.params_cb.ItemsSource = all_params
        self.params_cb.SelectedIndex = 0

    def _get_new_value(self, old_value):
        try:
            return coreutils.reformat_string(old_value,
                                             self.orig_format_tb.Text,
                                             self.new_format_tb.Text)
        except Exception:
            return ''

    def on_param_change(self, sender, args):
        self.preview_dg.ItemsSource = None
        revalue_items = []
        for element in self._target_elements:
            if self.selected_param == 'Name':
                old_value = revit.ElementWrapper(element).name
                new_value = self._get_new_value(old_value)
            else:
                param = element.LookupParameter(self.selected_param)
                if param:
                    old_value = param.AsString()
                    new_value = self._get_new_value(old_value)

            revalue_items.append(ReValueItem(oldvalue=old_value,
                                             newvalue=new_value))

        self.preview_dg.ItemsSource = revalue_items

    def apply_new_values(self, sender, args):
        pass


ReValueWindow('ReValueWindow.xaml').show(modal=True)
