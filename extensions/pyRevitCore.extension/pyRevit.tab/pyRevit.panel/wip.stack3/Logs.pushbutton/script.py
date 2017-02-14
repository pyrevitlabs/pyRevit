"""pyRevit log viewer for debugging"""

import os.path as op
import re
import clr

from pyrevit import USER_DESKTOP
from pyrevit.coreutils import verify_directory, cleanup_filename
from scriptutils import this_script, open_url, logger
from scriptutils.userinput import WPFWindow

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


class LogMessageListItem(object):
    def __init__(self, log_entry):
        self._log_entry = log_entry
        self.date, self.time, self.type, self.module, self.message = log_entry_parser.findall(self._log_entry)[0]


class LogViewerWindow(WPFWindow):
    def __init__(self, xaml_file_name):
        WPFWindow.__init__(self, xaml_file_name)

        self.logitems_lb.ItemsSource = []

        # with open(r'C:\Users\eirannejad\Desktop\pyRevit_2016_eirannejad_3180.log', 'r') as log_file:
        #     for log_entry in log_file.readlines():
        #         self.logitems_lb.ItemsSource.append(LogMessageListItem(log_entry))

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def handle_url_click(self, sender, args):
        open_url('https://github.com/McCulloughRT/PrintFromIndex')

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def selection_changed(self, sender, args):
        pass

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def load_log_file(self, sender, args):
        pass



if __name__ == '__main__':
    LogViewerWindow('LogViewerWindow.xaml').ShowDialog()
