"""pyRevit usage records viewer for debugging"""

import os.path as op
import re
import clr

from pyrevit.coreutils import verify_directory, cleanup_filename
import pyrevit.usagelog as usagelog
import pyrevit.usagelog.db as logdb
from scriptutils import this_script, logger
from scriptutils.userinput import WPFWindow, pick_folder

# noinspection PyUnresolvedReferences
from System.Windows.Forms import Clipboard
# noinspection PyUnresolvedReferences
from Autodesk.Revit.UI import TaskDialog


__title__ = 'Usage\nRecords'


class UsageRecordsWindow(WPFWindow):
    def __init__(self, xaml_file_name):
        WPFWindow.__init__(self, xaml_file_name)

        self.hide_element(self.clrsearch_b)
        self.hide_element(self.commandresults_dg)
        self.usagelogdir_tb.IsReadOnly = True

        self._update_cur_logpath()

    @property
    def cur_logfile_path(self):
        return self.usagelogdir_tb.Text

    @cur_logfile_path.setter
    def cur_logfile_path(self, value):
        self.usagelogdir_tb.Text = value
        self._update_records()
        self._update_filters()

    @property
    def record_list(self):
        return self.records_lb.ItemsSource

    @record_list.setter
    def record_list(self, value):
        self.records_lb.ItemsSource = value

    @property
    def current_filter(self):
        return self.filter_cb.SelectedItem

    @current_filter.setter
    def current_filter(self, rec_filter):
        # idx = self.filter_cb.ItemsSource.index(filter)
        self.filter_cb.SelectedItem = rec_filter

    @property
    def current_filter_list(self):
        return self.filter_cb.ItemsSource

    @property
    def current_search_term(self):
        return self.search_tb.Text

    @property
    def current_record(self):
        return self.records_lb.SelectedItem

    def _update_cur_logpath(self, logfile_path=None):
        self.cur_logfile_path = usagelog.get_current_usage_logpath() if not logfile_path else logfile_path

    def _update_records(self):
        recordfilter = self.current_filter
        search_term = self.current_search_term
        source_path = self.cur_logfile_path
        log_records = logdb.get_records(source_path=source_path,
                                        record_filter=recordfilter, search_term=search_term)
        if log_records:
            self.record_list = log_records
        else:
            self.record_list = []

    def _update_filters(self):
        self.filter_cb.ItemsSource = logdb.get_auto_filters(self.record_list)
        self.filter_cb.SelectedIndex = 0

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def search_txt_changed(self, sender, args):
        if self.search_tb.Text == '':
            self.hide_element(self.clrsearch_b)
        else:
            self.show_element(self.clrsearch_b)

        self._update_records()

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def clear_search(self, sender, args):
        self.search_tb.Text = ' '
        self.search_tb.Clear()

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def filter_changed(self, sender, args):
        self._update_records()

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def clear_filter(self, sender, args):
        self.filter_cb.SelectedIndex = 0

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def record_entry_changed(self, sender, args):
        class TableData:
            pass

        if self.current_record and self.current_record.commandresults:
            table_data = []
            for k,v in self.current_record.commandresults.items():
                td = TableData()
                td.key = k
                td.value = v
                table_data.append(td)
            self.commandresults_dg.ItemsSource = sorted(table_data, key=lambda d: d.key)
            self.show_element(self.commandresults_dg)
        else:
            self.hide_element(self.commandresults_dg)

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def filter_thissession_records(self, sender, args):
        for rec_filter in self.current_filter_list:
            if self.current_record.sessionid in rec_filter.filter_name:
                self.current_filter = rec_filter
                self._update_records()
                return True

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def copy_record_revit(self, sender, args):
        Clipboard.SetText(self.current_record.revit)

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def copy_record_revitbuild(self, sender, args):
        Clipboard.SetText(self.current_record.revitbuild)

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def copy_record_pyrevit(self, sender, args):
        Clipboard.SetText(self.current_record.pyrevit)

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def copy_record_script(self, sender, args):
        Clipboard.SetText(self.current_record.scriptpath)

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def copy_record_commandresults(self, sender, args):
        Clipboard.SetText(unicode(self.current_record.commandresults))

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def copy_record_originalrecord(self, sender, args):
        Clipboard.SetText(unicode(self.current_record.original_record))

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def load_log_file(self, sender, args):
        selected_path = pick_folder()
        if selected_path:
            self.cur_logfile_path = selected_path


if __name__ == '__main__':
    UsageRecordsWindow('UsageRecordsWindow.xaml').ShowDialog()
