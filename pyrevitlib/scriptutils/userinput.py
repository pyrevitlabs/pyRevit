import os
import os.path as op
import clr

from pyrevit.coreutils.logger import get_logger

clr.AddReference('IronPython.Wpf')
clr.AddReference('PresentationCore')
clr.AddReferenceByPartialName("PresentationFramework")
clr.AddReferenceByPartialName('System.Windows.Forms')
clr.AddReferenceByPartialName('WindowsBase')

# noinspection PyUnresolvedReferences
import System.Windows
# noinspection PyUnresolvedReferences
from System import Uri
# noinspection PyUnresolvedReferences
from System.Windows import Window
# noinspection PyUnresolvedReferences
from System.Windows.Forms import FolderBrowserDialog, DialogResult, OpenFileDialog
# noinspection PyUnresolvedReferences
from System.Windows.Controls import SelectionMode
# noinspection PyUnresolvedReferences
from System.Windows.Media.Imaging import BitmapImage
# noinspection PyUnresolvedReferences
from System.IO import StringReader
# noinspection PyUnresolvedReferences
import wpf


logger = get_logger(__name__)


class WPFWindow(Window):
    def __init__(self, xaml_file, literal_string=False):
        self.Parent = self
        if not literal_string:
            if not op.exists(xaml_file):
                # noinspection PyUnresolvedReferences
                wpf.LoadComponent(self, os.path.join(__commandpath__, xaml_file))
            else:
                wpf.LoadComponent(self, xaml_file)
        else:
            wpf.LoadComponent(self, StringReader(xaml_file))

    def set_image_source(self, element_name, image_file):
        wpf_element = getattr(self, element_name)
        if not op.exists(image_file):
            # noinspection PyUnresolvedReferences
            wpf_element.Source = BitmapImage(Uri(os.path.join(__commandpath__, image_file)))
        else:
            wpf_element.Source = BitmapImage(Uri(image_file))

    @staticmethod
    def hide_element(*wpf_elements):
        for wpf_element in wpf_elements:
            wpf_element.Visibility = System.Windows.Visibility.Collapsed

    @staticmethod
    def show_element(*wpf_elements):
        for wpf_element in wpf_elements:
            wpf_element.Visibility = System.Windows.Visibility.Visible


class SelectFromList(WPFWindow):
    layout = """
    <Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
            xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
            ShowInTaskbar="False" ResizeMode="NoResize"
            WindowStartupLocation="CenterScreen" HorizontalContentAlignment="Center">
            <DockPanel Margin="10">
                <Button Content="Select" Click="button_select" DockPanel.Dock="Bottom" Margin="0,10,0,0"/>
                <ListView x:Name="list_lb" />
            </DockPanel>
    </Window>
    """
    def __init__(self, option_list, title, width, height, multiselect):
        WPFWindow.__init__(self, SelectFromList.layout, literal_string=True)
        self.Title = title
        self.Width = width
        self.Height = height
        self.list_lb.SelectionMode = SelectionMode.Extended if multiselect else SelectionMode.Single
        self.list_lb.ItemsSource = option_list
        self.selected = None

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def button_select(self, sender, args):
        self.selected = self.list_lb.SelectedItems
        self.Close()

    @classmethod
    def show(cls, option_list, title='Select from list', width=300, height=400, multiselect=True):
        dlg = cls(option_list, title, width, height, multiselect)
        dlg.ShowDialog()
        return dlg.selected


class CommandSwitchWindow:
    def __init__(self, switches, message='Pick a command option:'):
        self.Parent = self
        self.selected_switch = ''
        # Create window
        self.my_window = System.Windows.Window()
        self.my_window.WindowStyle = System.Windows.WindowStyle.None
        self.my_window.AllowsTransparency = True
        self.my_window.Background = None
        self.my_window.Title = 'Command Options'
        self.my_window.Width = 600
        self.my_window.SizeToContent = System.Windows.SizeToContent.Height
        self.my_window.ResizeMode = System.Windows.ResizeMode.CanMinimize
        self.my_window.WindowStartupLocation = System.Windows.WindowStartupLocation.CenterScreen
        self.my_window.PreviewKeyDown += self.handle_esc_key
        self.my_window.MouseUp += self.handle_click
        border = System.Windows.Controls.Border()
        border.CornerRadius = System.Windows.CornerRadius(15)
        border.Background = System.Windows.Media.SolidColorBrush(System.Windows.Media.Color.FromArgb(220, 55, 50, 50))
        self.my_window.Content = border

        # Create StackPanel to Layout UI elements
        stack_panel = System.Windows.Controls.StackPanel()
        stack_panel.Margin = System.Windows.Thickness(5)
        border.Child = stack_panel

        label = System.Windows.Controls.Label()
        label.Foreground = System.Windows.Media.Brushes.White
        label.Content = message
        label.Margin = System.Windows.Thickness(2, 0, 0, 0)
        stack_panel.Children.Add(label)

        # Create WrapPanel for command options
        self.button_list = System.Windows.Controls.WrapPanel()
        self.button_list.Margin = System.Windows.Thickness(5)
        stack_panel.Children.Add(self.button_list)

        for switch in switches:
            my_button = System.Windows.Controls.Button()
            my_button.BorderBrush = System.Windows.Media.Brushes.Black
            my_button.BorderThickness = System.Windows.Thickness(0)
            my_button.Content = switch
            my_button.Margin = System.Windows.Thickness(5, 0, 5, 5)
            my_button.Padding = System.Windows.Thickness(5, 0, 5, 0)
            my_button.Click += self.process_switch
            self.button_list.Children.Add(my_button)

    # noinspection PyUnusedLocal
    def handle_click(self, sender, args):
        self.my_window.Close()

    # noinspection PyUnusedLocal
    def handle_esc_key(self, sender, args):
        if args.Key == System.Windows.Input.Key.Escape:
            self.my_window.Close()

    # noinspection PyUnusedLocal
    def process_switch(self, sender, args):
        self.my_window.Close()
        self.selected_switch = sender.Content

    def pick_cmd_switch(self):
        self.my_window.ShowDialog()
        return self.selected_switch


def pick_folder():
    fb_dlg = FolderBrowserDialog()
    if fb_dlg.ShowDialog() == DialogResult.OK:
        return fb_dlg.SelectedPath


def pick_file(file_ext='', multi_file=False):
    of_dlg = OpenFileDialog()
    of_dlg.Filter = '|*.{}'.format(file_ext)
    of_dlg.RestoreDirectory = True
    of_dlg.Multiselect = multi_file
    if of_dlg.ShowDialog() == DialogResult.OK:
        return of_dlg.FileName
