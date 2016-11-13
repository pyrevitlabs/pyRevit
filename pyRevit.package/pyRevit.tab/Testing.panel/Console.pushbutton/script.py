from pyrevit.config import SESSION_STAMPED_ID
from pyrevit.utils import Timer

from System import AppDomain

# _scriptSource = "";
# _alternateScriptSource = "";
# _logfilename = "";
# _forcedDebugMode = false;
# _syspaths;
# _cmdName;
# _cmdOptions;

cmds = []
cmd_names = []

t = Timer()

for assm in AppDomain.CurrentDomain.GetAssemblies():
    if SESSION_STAMPED_ID in assm.FullName:
        for cmd_type in assm.GetTypes():
            cmds.append(cmd_type())

# print('Done. found {} commands in {}'.format(len(cmds), t.get_time_hhmmss()))

import clr
clr.AddReferenceByPartialName('PresentationCore')
clr.AddReferenceByPartialName("PresentationFramework")
# clr.AddReferenceByPartialName('System.Windows.Forms')
import System.Windows


class ConsoleWindow:
    def __init__(self):
        self.my_window = System.Windows.Window()
        self.my_window.Title = 'Console'
        self.my_window.Width = 800
        self.my_window.Height = 100
        self.my_window.WindowStartupLocation = System.Windows.WindowStartupLocation.CenterScreen

        self.my_stack = System.Windows.Controls.StackPanel()
        self.my_stack.Margin = System.Windows.Thickness(5)
        self.my_window.Content = self.my_stack

        self.console_input = System.Windows.Controls.ComboBox()
        self.console_input.IsEditable = True
        self.console_input.Margin = System.Windows.Thickness(30, 0, 30, 0)
        self.my_stack.Children.Add(self.console_input)

        self.console_input.KeyUp += self.filter_cmds
        self.console_input.ItemsSource = [x._cmdName for x in cmds]
        self.typed = ''

        self.filtered_cmds = cmds

    def filter_cmds(self, sender, args):
        txtbox = self.console_input.Template.FindName("PART_EditableTextBox", self.console_input)
        if self.filtered_cmds:
            c_index = txtbox.CaretIndex
            self.typed += str(args.Key).lower()
            self.filtered_cmds = [x for x in self.filtered_cmds if str(x._cmdName).lower().startswith(self.typed)]
            self.console_input.ItemsSource = [x._cmdName for x in self.filtered_cmds]
            self.console_input.SelectedIndex = 0
            txtbox.CaretIndex = c_index

    def showwindow(self):
        self.my_window.ShowDialog()


ConsoleWindow().showwindow()