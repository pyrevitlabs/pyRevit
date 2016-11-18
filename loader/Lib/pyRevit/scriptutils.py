import os
import os.path as op

from .logger import get_logger
from .utils import get_all_subclasses
from .exceptions import PyRevitException
from .loader.components import GenericCommand

logger = get_logger(__name__)


import clr
clr.AddReferenceByPartialName('PresentationCore')
clr.AddReferenceByPartialName("PresentationFramework")
clr.AddReferenceByPartialName('System.Windows.Forms')
clr.AddReferenceByPartialName('WindowsBase')
import System.Windows


class commandSwitches:
    def __init__(self, switches, message = 'Pick a command option:'):
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
        self.my_window.PreviewKeyDown += self.handleEsc
        border = System.Windows.Controls.Border()
        border.CornerRadius  = System.Windows.CornerRadius(15)
        border.Background = System.Windows.Media.SolidColorBrush(System.Windows.Media.Color.FromArgb(220,55,50,50))
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
            my_button.Click += self.processSwitch
            self.button_list.Children.Add(my_button)


    def handleEsc(self, sender, args):
        if (args.Key == System.Windows.Input.Key.Escape):
            self.my_window.Close()


    def processSwitch(self, sender, args):
        self.my_window.Close()
        self.selected_switch = sender.Content

    def pickCommandSwitch(self):
        self.my_window.ShowDialog()
        return self.selected_switch


def get_script_info(script_file_addr):
    script_dir = op.dirname(script_file_addr)
    for component_type in get_all_subclasses([GenericCommand]):
        logger.debug('Testing sub_directory {} for {}'.format(script_dir, component_type))
        try:
            # if cmp_class can be created for this sub-dir, the add to list
            # cmp_class will raise error if full_path is not of cmp_class type.
            component = component_type()
            component.__init_from_dir__(script_dir)
            logger.debug('Successfuly created component: {} from: {}'.format(component, script_dir))
            return component
        except PyRevitException:
            logger.debug('Can not create component of type: {} from: {}'.format(component_type, script_dir))
    return None


def get_ui_button():
    # fixme: implement get_ui_button
    pass


def get_temp_file():
    """Returns a filename to be used by a user script to store temporary information.
    Temporary files are saved in USER_TEMP_DIR.
    """
    # fixme temporary file
    pass
