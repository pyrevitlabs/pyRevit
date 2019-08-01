"""Reformat parameter string values (Super handy for renaming elements)"""
#pylint: disable=E0401,W0703,W0613
from pyrevit import coreutils
from pyrevit import revit, DB
from pyrevit import forms


__context__ = "selection"
__helpurl__ = "{{docpath}}-JDgiP3gK9Y"


class ReValueItem(object):
    def __init__(self, eid, oldvalue, final=False):
        self.eid = eid
        self.oldvalue = oldvalue
        self.newvalue = ''
        self.final = final
        self.tooltip = ''

    def format_value(self, old_format, new_format):
        try:
            if old_format and new_format:
                self.newvalue = coreutils.reformat_string(self.oldvalue,
                                                          old_format,
                                                          new_format)
                self.tooltip = '{} --> {}'.format(old_format, new_format)
            else:
                self.tooltip = 'No Conversion Specified'
        except Exception:
            self.newvalue = ''


class ReValueWindow(forms.WPFWindow):
    def __init__(self, xaml_file_name):
        # create pattern maker window and process options
        forms.WPFWindow.__init__(self, xaml_file_name)
        self._target_elements = revit.get_selection().elements
        self._reset_preview()
        self._setup_params()

    @property
    def selected_param(self):
        return self.params_cb.SelectedItem

    @property
    def old_format(self):
        return self.orig_format_tb.Text

    @old_format.setter
    def old_format(self, value):
        self.orig_format_tb.Text = value

    @property
    def new_format(self):
        return self.new_format_tb.Text

    @property
    def preview_items(self):
        return self.preview_dg.ItemsSource

    @property
    def selected_preview_items(self):
        return self.preview_dg.SelectedItems

    def _setup_params(self):
        unique_params = set()
        for element in self._target_elements:
            # grab element parameters
            for param in element.Parameters:
                if not param.IsReadOnly \
                        and param.StorageType == DB.StorageType.String:
                    unique_params.add(param.Definition.Name)
            # grab element family parameters
            # if element.Family:
            #     for param in element.Family.Parameters:
            #         if not param.IsReadOnly \
            #                 and param.StorageType == DB.StorageType.String:
            #             unique_params.add(
            #                 'Family: {}'.format(param.Definition.Name)
            #                 )

        all_params = ['Name', 'Family: Name']
        all_params.extend(sorted(list(unique_params)))
        self.params_cb.ItemsSource = all_params
        self.params_cb.SelectedIndex = 0

    def _reset_preview(self):
        self._revalue_items = []
        self.preview_dg.ItemsSource = self._revalue_items

    def _refresh_preview(self):
        self.preview_dg.Items.Refresh()

    def on_param_change(self, sender, args):
        self._reset_preview()
        for element in self._target_elements:
            old_value = ''
            if self.selected_param == 'Name':
                old_value = revit.query.get_name(element)
            elif self.selected_param == 'Family: Name':
                if hasattr(element, 'Family') and element.Family:
                    old_value = revit.query.get_name(element.Family)
            # elif 'Family:' in self.selected_param:
            #     if element.Family:
            #         pname = self.selected_param.replace('Family: ', '')
            #         param = element.Family.LookupParameter(pname)
            #         if param:
            #             old_value = param.AsString()
            else:
                param = element.LookupParameter(self.selected_param)
                if param:
                    old_value = param.AsString()

            newitem = ReValueItem(eid=element.Id, oldvalue=old_value)
            newitem.format_value(self.old_format,
                                 self.new_format)
            self._revalue_items.append(newitem)
        self._refresh_preview()

    def on_format_change(self, sender, args):
        for item in self._revalue_items:
            if not item.final:
                item.format_value(self.old_format,
                                  self.new_format)
        self._refresh_preview()

    def on_selection_change(self, sender, args):
        if self.preview_dg.SelectedItems.Count == 1 \
                and not self.new_format:
            self.old_format = self.preview_dg.SelectedItem.oldvalue

    def mark_as_final(self, sender, args):
        selected_names = [x.eid for x in self.selected_preview_items]
        for item in self._revalue_items:
            if item.eid in selected_names:
                item.final = True
        self._refresh_preview()

    def apply_new_values(self, sender, args):
        self.Close()
        try:
            with revit.Transaction('ReValue {}'.format(self.selected_param),
                                   log_errors=False):
                for item in self._revalue_items:
                    if item.newvalue:
                        element = revit.doc.GetElement(item.eid)
                        if self.selected_param == 'Name':
                            element.Name = item.newvalue
                        elif self.selected_param == 'Family: Name':
                            if element.Family:
                                element.Family.Name = item.newvalue
                        else:
                            param = element.LookupParameter(self.selected_param)
                            if param:
                                param.Set(item.newvalue)
        except Exception as ex:
            forms.alert(str(ex), title='Error')


ReValueWindow('ReValueWindow.xaml').show(modal=True)
