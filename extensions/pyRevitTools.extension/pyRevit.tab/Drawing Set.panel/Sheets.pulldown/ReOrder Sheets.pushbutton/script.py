"""Print items in order from a sheet index.

This tool looks for project parameters (on Sheets) that are
Instance, of type Integer, and have "Order" in their names.
"""
#pylint: disable=W0613,E0401,C0103
import re

from pyrevit import forms
from pyrevit import revit, DB
from pyrevit import script


logger = script.get_logger()


class ListItem(object):
    def __init__(self, view_sheet):
        self._item = view_sheet
        self.name = self._item.Name
        self.number = self._item.SheetNumber
        self.printable = self._item.CanBePrinted
        self.order_index = 0

    @property
    def revit_item(self):
        return self._item


class ReOrderWindow(forms.WPFWindow):
    def __init__(self, xaml_file_name):
        forms.WPFWindow.__init__(self, xaml_file_name)

        self._config = script.get_config()

        self._setup_item_params_combobox()

        self.grouping_pattern = \
            self._config.get_option('index_grouping_pattern',
                                    r'([A-Z])\d')

    @property
    def items_list(self):
        return self.items_dg.ItemsSource or []

    @items_list.setter
    def items_list(self, value):
        self.items_dg.ItemsSource = value
        # update oder indices
        self._update_order_indices()

    @property
    def selected_item_param(self):
        return self.orderparams_cb.SelectedItem

    @property
    def grouping_pattern(self):
        pattern = self.indexgroup_tb.Text
        try:
            re.compile(pattern)
            return pattern
        except Exception:
            return ""

    @grouping_pattern.setter
    def grouping_pattern(self, value):
        self.indexgroup_tb.Text = value

    def _refresh(self):
        existing_items = self.items_list
        self.items_list = []
        self.items_list = existing_items

    def _update_order_indices(self):
        if self.grouping_pattern:
            last_groupid = ''
            grouping_index = 0
            grouping_range = 1000
            for idx, item in enumerate(self.items_list):
                match = re.search(self.grouping_pattern, item.number)
                if match and match.groups():
                    groupid = match.groups()[0]
                    if groupid != last_groupid:
                        last_groupid = groupid
                        grouping_index += 1

                    item.order_index = (grouping_range * grouping_index) + idx
                else:
                    item.order_index = idx
        else:
            for idx, item in enumerate(self.items_list):
                item.order_index = idx

    def _setup_item_params_combobox(self):
        items = revit.query.get_sheets()
        if items:
            item_sample = items[0]
            item_params = [x.Definition.Name for x in item_sample.Parameters
                           if x.StorageType == DB.StorageType.Integer]

            order_params = [x for x in item_params if 'order' in x.lower()]
            self.orderparams_cb.ItemsSource = sorted(order_params)
            self.orderparams_cb.SelectedIndex = 0

    def _get_ordered_items(self):
        items = revit.query.get_sheets(include_noappear=False)
        if self.selected_item_param:
            items = sorted(
                items,
                key=lambda x: x.LookupParameter(self.selected_item_param)
                .AsInteger()
                )
        return items

    def _get_selected_nonselected(self):
        selected = list(self.items_dg.SelectedItems)
        nonselected = []
        for item in self.items_list:
            if item not in selected:
                nonselected.append(item)
        return selected, nonselected

    def _insert_list_in_list(self, src_list, dest_list, index):
        max_index = len(dest_list)
        if index < 0:
            index = 0

        if index > max_index:
            index = max_index

        for item in reversed(src_list):
            dest_list.insert(index, item)

        return dest_list

    def selection_changed(self, sender, args):
        if self.selected_item_param:
            items_list = [ListItem(x) for x in self._get_ordered_items()]
            # Show all items
            self.items_list = items_list

    def sorting_changed(self, sender, args):
        order_param = args.Column.SortMemberPath
        if order_param == 'number':
            self.items_list = sorted(self.items_list, key=lambda x: x.number)
        elif order_param == 'name':
            self.items_list = sorted(self.items_list, key=lambda x: x.name)

    def grouping_pattern_changed(self, sender, args):
        self._refresh()

    def move_to_top(self, sender, args):
        selected, non_selected = self._get_selected_nonselected()
        new_list = self._insert_list_in_list(selected, non_selected, 0)
        self.items_list = new_list

    def move_10_to_top(self, sender, args):
        selected, non_selected = self._get_selected_nonselected()
        index = self.items_dg.ItemsSource.index(selected[0])
        new_list = self._insert_list_in_list(selected, non_selected, index - 10)
        self.items_list = new_list

    def move_1_to_top(self, sender, args):
        selected, non_selected = self._get_selected_nonselected()
        index = self.items_dg.ItemsSource.index(selected[0])
        new_list = self._insert_list_in_list(selected, non_selected, index - 1)
        self.items_list = new_list

    def move_1_to_bottom(self, sender, args):
        selected, non_selected = self._get_selected_nonselected()
        index = self.items_dg.ItemsSource.index(selected[0])
        new_list = self._insert_list_in_list(selected, non_selected, index + 1)
        self.items_list = new_list

    def move_10_to_bottom(self, sender, args):
        selected, non_selected = self._get_selected_nonselected()
        index = self.items_dg.ItemsSource.index(selected[0])
        new_list = self._insert_list_in_list(selected, non_selected, index + 10)
        self.items_list = new_list

    def move_to_bottom(self, sender, args):
        selected, non_selected = self._get_selected_nonselected()
        new_list = self._insert_list_in_list(selected,
                                             non_selected,
                                             len(non_selected))
        self.items_list = new_list

    def reorder_items(self, sender, args):
        self.Close()
        self._config.set_option('index_grouping_pattern',
                                self.grouping_pattern)
        with revit.Transaction('Reorder Sheets'):
            for item in self.items_list:
                idx_param = \
                    item.revit_item.LookupParameter(self.selected_item_param)
                if idx_param:
                    idx_param.Set(item.order_index)


ReOrderWindow('ReOrderWindow.xaml').ShowDialog()
