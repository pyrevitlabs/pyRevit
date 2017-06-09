import os
import os.path as op
import clr

from pyrevit import HOST_APP
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
from System.Windows.Media import SolidColorBrush, Color
# noinspection PyUnresolvedReferences
from System.Windows.Media.Imaging import BitmapImage
# noinspection PyUnresolvedReferences
from System.Windows.Forms import Screen
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


class TemplatePromptBar(WPFWindow):
    layout = """
    <Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
            xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
            WindowStyle="None" Background="{x:Null}" ShowInTaskbar="False" ShowActivated="False"
            WindowStartupLocation="Manual" ResizeMode="NoResize" Topmost="True"
            ScrollViewer.VerticalScrollBarVisibility="Disabled">
        <Grid Background="#FFEA9F00">
            <TextBlock x:Name="message_tb"
                       TextWrapping="Wrap" Text="TextBlock" TextAlignment="Center" VerticalAlignment="Center"
                       Foreground="{DynamicResource {x:Static SystemColors.WindowBrushKey}}"/>
        </Grid>    
    </Window>
    """

    def __init__(self, title='Message', height=24, **kwargs):
        WPFWindow.__init__(self, self.layout, literal_string=True)
        screen = HOST_APP.proc_screen
        work_area = screen.WorkingArea
        self.Top = work_area.Top
        self.Left = work_area.Left
        self.Width = work_area.Width
        self.Height = height
        self.message_tb.Text = title
        self._setup(**kwargs)

    def _setup(self, **kwargs):
        pass

    def __enter__(self):
        self.Show()

    def __exit__(self, exception, exception_value, traceback):
        self.Close()


class WarningBar(TemplatePromptBar):
    pass
