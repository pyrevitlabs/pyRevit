"""pyRevit log viewer for debugging"""

import os.path as op
import re
import clr

from pyrevit import USER_DESKTOP
from pyrevit.coreutils.logger import FILE_LOG_FILENAME
from pyrevit.coreutils import verify_directory, cleanup_filename
from pyrevit.coreutils import appdata
from scriptutils import this_script, open_url, logger
from scriptutils.userinput import WPFWindow, pick_file

clr.AddReference('PresentationCore')
clr.AddReferenceByPartialName("PresentationFramework")

# noinspection PyUnresolvedReferences
from System.Windows import DragDrop, DragDropEffects
# noinspection PyUnresolvedReferences
from System.Windows import Setter, EventSetter, DragEventHandler, Style
# noinspection PyUnresolvedReferences
from System.Windows.Input import MouseButtonEventHandler
# noinspection PyUnresolvedReferences
from System.Windows.Controls import ListViewItem


log_entry_parser = re.compile('(\d{4}-\d{2}-\d{2})\s{1}(\d{2}:\d{2}:\d{2},\d{3})\s{1}(.*)\:\s{1}\[(.*?)\]\s{1}(.+)')


class EntryFilter:
    type_id = ''

    def __init__(self, filter_type):
        self.filter_type = filter_type

    def __eq__(self, other):
        return self.filter_type == other.filter_type

    def __hash__(self):
        return hash((self.filter_type))

    def filter_entries(self, entry_list, search_term=None):
        filtered_list = []
        for entry in entry_list:
            if getattr(entry, self.type_id) == self.filter_type:
                if search_term:
                    if search_term.lower() in entry.message.lower() \
                    or search_term.lower() in entry.clean_msg.lower():
                        filtered_list.append(entry)
                else:
                    filtered_list.append(entry)
        return filtered_list


class EntryNoneFilter(EntryFilter):
    type_id = 'none'
    def __init__(self):
        self.filter_type = 'None'

    def filter_entries(self, entry_list, search_term=None):
        if search_term:
            filtered_list = []
            for entry in entry_list:
                if search_term.lower() in entry.message.lower() \
                or search_term.lower() in entry.clean_msg.lower():
                    filtered_list.append(entry)
            return filtered_list
        else:
            return entry_list


class EntryTypeFilter(EntryFilter):
    type_id = 'type'


class EntryDateFilter(EntryFilter):
    type_id = 'date'


class EntryModuleFilter(EntryFilter):
    type_id = 'module'


class LogMessageListItem(object):
    def __init__(self, log_entry):
        self._log_entry = log_entry
        self.date, self.time, self.type, self.module, self.message = log_entry_parser.findall(self._log_entry)[0]

    @property
    def clean_msg(self):
        return self.message.replace('&clt;', '<').replace('&cgt;', '>')


class LogViewerWindow(WPFWindow):
    def __init__(self, xaml_file_name):
        WPFWindow.__init__(self, xaml_file_name)

        self.hide_element(self.clrsearch_b)
        self._current_entry_list = list()
        self._log_files = {op.basename(f):f for f in appdata.list_data_files('log')}
        self.logfiles_cb.ItemsSource = self._log_files.keys()
        if FILE_LOG_FILENAME in self._log_files.keys():
            self.logfiles_cb.SelectedIndex = self.logfiles_cb.ItemsSource.index(FILE_LOG_FILENAME)
        else:
            self.logfiles_cb.SelectedIndex = 0

    @property
    def current_log_file(self):
        return self.logfiles_cb.SelectedItem

    @property
    def current_log_entry(self):
        return self.logitems_lb.SelectedItem

    @property
    def current_filter(self):
        return self.filter_cb.SelectedItem

    def _read_log_file(self, file_path):
        entry_list = []
        log_file_line = 1
        prev_entry = None
        with open(file_path, 'r') as log_file:
            for log_entry in log_file.readlines():
                try:
                    new_entry = LogMessageListItem(log_entry)
                    entry_list.append(new_entry)
                    log_file_line += 1
                    prev_entry = new_entry
                except Exception as err:
                    logger.debug('Error processing entry at {}:{}'.format(op.basename(file_path), log_file_line))
                    prev_entry.message += log_entry
                    log_file_line += 1

        return entry_list

    def _append_log_file(self, log_file):
        base_name = op.basename(log_file)
        self._log_files[base_name] = log_file
        self.logfiles_cb.ItemsSource = self._log_files.keys()
        self.logfiles_cb.SelectedIndex = self.logfiles_cb.ItemsSource.index(base_name)

    @staticmethod
    def _extract_filters(log_entry_list):
        filter_list = [EntryNoneFilter()]
        entry_types = set()
        entry_modules = set()
        entry_dates = set()

        for log_entry in log_entry_list:
            entry_types.add(EntryTypeFilter(log_entry.type))
            entry_modules.add(EntryModuleFilter(log_entry.module))
            entry_dates.add(EntryDateFilter(log_entry.date))

        filter_list.extend(entry_types)
        filter_list.extend(entry_modules)
        filter_list.extend(entry_dates)

        return filter_list

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def log_file_changed(self, sender, args):
        self._current_entry_list = self._read_log_file(self._log_files[self.current_log_file])
        filter_list = self._extract_filters(self._current_entry_list)

        self.logitems_lb.ItemsSource = self._current_entry_list
        self.logitems_lb.ScrollIntoView(self.logitems_lb.Items[0])

        self.filter_cb.ItemsSource = filter_list
        self.filter_cb.SelectedIndex = 0

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def filter_changed(self, sender, args):
        cur_filter = self.current_filter
        # self.logitems_lb.UnselectAll()
        if cur_filter:
            filtered_list = cur_filter.filter_entries(self._current_entry_list, search_term=self.search_tb.Text)
            self.logitems_lb.ItemsSource = filtered_list
        else:
            self.logitems_lb.ItemsSource = self._current_entry_list

        self.logitems_lb.ScrollIntoView(self.current_log_entry)

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def search_txt_changed(self, sender, args):
        if self.search_tb.Text == '':
            self.hide_element(self.clrsearch_b)
        else:
            self.show_element(self.clrsearch_b)

        cur_filter = self.current_filter
        if cur_filter:
            filtered_list = cur_filter.filter_entries(self._current_entry_list, search_term=self.search_tb.Text)
            self.logitems_lb.ItemsSource = filtered_list
        else:
            self.logitems_lb.ItemsSource = self._current_entry_list

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def clear_search(self, sender, args):
        self.search_tb.Text = ' '
        self.search_tb.Clear()

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def log_entry_changed(self, sender, args):
        # self.entrymsg_tb.Navigate("about:blank")
        # self.entrymsg_tb.Document.Write('<html><head></head><body>')
        # self.entrymsg_tb.Document.Write(self.current_log_entry.clean_msg)
        if self.current_log_entry:
            self.entrymsg_tb.Text = self.current_log_entry.clean_msg

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def load_log_file(self, sender, args):
        self._append_log_file(pick_file('log'))


if __name__ == '__main__':
    LogViewerWindow('LogViewerWindow.xaml').ShowDialog()
