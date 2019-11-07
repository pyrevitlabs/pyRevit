"""pyRevit log viewer for debugging."""

import os.path as op
import re

from pyrevit.coreutils import logger
from pyrevit.coreutils import appdata
from pyrevit import forms
from pyrevit import forms
from pyrevit import script


__context__ = 'zero-doc'


slogger = script.get_logger()


log_entry_parser = re.compile('(\d{4}-\d{2}-\d{2})\s'
                              '{1}(\d{2}:\d{2}:\d{2},\d{3})\s'
                              '{1}(.*)\s'
                              '{1}\[(.*?)\]\s'
                              '{1}(.+)')

logging_command_parser = re.compile('<(.*)>\s(.*)')


class EntryFilter:
    type_id = ''
    name_template = ''

    def __init__(self, filter_value):
        self.filter_value = filter_value
        self.filter_name = self.name_template.format(self.filter_value)

    def __eq__(self, other):
        return self.filter_value == other.filter_value

    def __ne__(self, other):
        return self.filter_value != other.filter_value

    def __hash__(self):
        return hash(self.filter_value)

    def __lt__(self, other):
        return self.filter_value < other.filter_value

    def filter_entries(self, entry_list, search_term=None):
        filtered_list = []
        for entry in entry_list:
            if getattr(entry, self.type_id) == self.filter_value:
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
        self.filter_value = 'None'
        self.filter_name = 'No Filter'

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


class EntryLevelFilter(EntryFilter):
    type_id = 'level'
    name_template = 'Level: {}'


class EntryDateFilter(EntryFilter):
    type_id = 'date'
    name_template = 'Date: {}'


class EntryModuleFilter(EntryFilter):
    type_id = 'module'
    name_template = 'Module: {}'


class EntryCommandFilter(EntryFilter):
    type_id = 'command'
    name_template = 'Command: {}'


class LogMessageListItem(object):
    def __init__(self, log_entry):
        self._log_entry = log_entry
        self.date, self.time, \
            self.level, self.module, \
            self.message = log_entry_parser.findall(self._log_entry)[0]
        try:
            self.command, self.module = \
                logging_command_parser.findall(self.module)[0]
        except Exception as err:
            self.command = None

    @property
    def clean_msg(self):
        return self.message.replace('&clt;', '<').replace('&cgt;', '>')

    @property
    def is_command(self):
        return self.command


class LogViewerWindow(forms.WPFWindow):
    def __init__(self, xaml_file_name):
        forms.WPFWindow.__init__(self, xaml_file_name)

        self.hide_element(self.clrsearch_b)
        self._current_entry_list = []
        self._log_files = \
            {op.basename(f): f for f in appdata.list_data_files('log')}
        self.logfiles_cb.ItemsSource = self._log_files.keys()
        if logger.FILE_LOG_FILENAME in self._log_files.keys():
            self.logfiles_cb.SelectedIndex = \
                self.logfiles_cb.ItemsSource.index(logger.FILE_LOG_FILENAME)
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
        try:
            with open(file_path, 'r') as log_file:
                for log_entry in log_file.readlines():
                    try:
                        new_entry = LogMessageListItem(log_entry)
                        entry_list.append(new_entry)
                        log_file_line += 1
                        prev_entry = new_entry
                    except Exception as err:
                        slogger.debug('Error processing entry at {}:{}'
                                      .format(op.basename(file_path),
                                              log_file_line))
                        prev_entry.message += log_entry
                        log_file_line += 1
        except Exception as read_err:
            slogger.error('Error reading log file: {} | {}'
                          .format(file_path, read_err))

        return entry_list

    def _append_log_file(self, log_file):
        base_name = op.basename(log_file)
        self._log_files[base_name] = log_file
        self.logfiles_cb.ItemsSource = self._log_files.keys()
        self.logfiles_cb.SelectedIndex = \
            self.logfiles_cb.ItemsSource.index(base_name)

    @staticmethod
    def _extract_filters(log_entry_list):
        filter_list = [EntryNoneFilter()]
        entry_types = set()
        entry_modules = set()
        entry_dates = set()
        entry_commands = set()

        for log_entry in log_entry_list:
            entry_types.add(EntryLevelFilter(log_entry.level))
            entry_modules.add(EntryModuleFilter(log_entry.module))
            entry_dates.add(EntryDateFilter(log_entry.date))
            if log_entry.command:
                entry_commands.add(EntryCommandFilter(log_entry.command))

        filter_list.extend(sorted(entry_types))
        filter_list.extend(sorted(entry_modules))
        filter_list.extend(sorted(entry_dates))
        filter_list.extend(sorted(entry_commands))

        return filter_list

    def log_file_changed(self, sender, args):
        self._current_entry_list = \
            self._read_log_file(self._log_files[self.current_log_file])
        if self._current_entry_list:
            filter_list = self._extract_filters(self._current_entry_list)

            self.logitems_lb.ItemsSource = self._current_entry_list
            self.logitems_lb.ScrollIntoView(self.logitems_lb.Items[0])

            self.filter_cb.ItemsSource = filter_list
            self.filter_cb.SelectedIndex = 0

    def filter_changed(self, sender, args):
        cur_filter = self.current_filter
        # self.logitems_lb.UnselectAll()
        if cur_filter:
            filtered_list = \
                cur_filter.filter_entries(self._current_entry_list,
                                          search_term=self.search_tb.Text)
            self.logitems_lb.ItemsSource = filtered_list
        else:
            self.logitems_lb.ItemsSource = self._current_entry_list

        self.logitems_lb.ScrollIntoView(self.current_log_entry)

    def search_txt_changed(self, sender, args):
        if self.search_tb.Text == '':
            self.hide_element(self.clrsearch_b)
        else:
            self.show_element(self.clrsearch_b)

        cur_filter = self.current_filter
        if cur_filter:
            filtered_list = \
                cur_filter.filter_entries(self._current_entry_list,
                                          search_term=self.search_tb.Text)
            self.logitems_lb.ItemsSource = filtered_list
        else:
            self.logitems_lb.ItemsSource = self._current_entry_list

    def clear_search(self, sender, args):
        self.search_tb.Text = ' '
        self.search_tb.Clear()

    def log_entry_changed(self, sender, args):
        # self.entrymsg_tb.Navigate("about:blank")
        # self.entrymsg_tb.Document.Write('<html><head></head><body>')
        # self.entrymsg_tb.Document.Write(self.current_log_entry.clean_msg)
        if self.current_log_entry:
            self.entrymsg_tb.Text = self.current_log_entry.clean_msg

    def load_log_file(self, sender, args):
        selected_file = forms.pick_file('log')
        if selected_file:
            self._append_log_file(selected_file)


LogViewerWindow('LogViewerWindow.xaml').ShowDialog()
