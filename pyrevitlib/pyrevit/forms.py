import os
import os.path as op

from pyrevit import HOST_APP, EXEC_PARAMS
from pyrevit.coreutils.logger import get_logger
from pyrevit import platform
from pyrevit.revitapi import UI


logger = get_logger(__name__)


class WPFWindow(platform.Windows.Window):
    def __init__(self, xaml_file, literal_string=False):
        self.Parent = self
        if not literal_string:
            if not op.exists(xaml_file):
                platform.wpf.LoadComponent(
                    self,
                    os.path.join(EXEC_PARAMS.command_path,
                                 xaml_file)
                    )
            else:
                platform.wpf.LoadComponent(self, xaml_file)
        else:
            platform.wpf.LoadComponent(self, platform.StringReader(xaml_file))

    def show(self):
        return self.Show()

    def show_dialog(self):
        return self.ShowDialog()

    def set_image_source(self, element_name, image_file):
        wpf_element = getattr(self, element_name)
        if not op.exists(image_file):
            # noinspection PyUnresolvedReferences
            wpf_element.Source = \
                platform.Imaging.BitmapImage(
                    platform.Uri(os.path.join(EXEC_PARAMS.command_path,
                                              image_file))
                    )
        else:
            wpf_element.Source = \
                platform.Imaging.BitmapImage(platform.Uri(image_file))

    @staticmethod
    def hide_element(*wpf_elements):
        for wpf_element in wpf_elements:
            wpf_element.Visibility = platform.Windows.Visibility.Collapsed

    @staticmethod
    def show_element(*wpf_elements):
        for wpf_element in wpf_elements:
            wpf_element.Visibility = platform.Windows.Visibility.Visible


class TemplatePromptBar(WPFWindow):
    layout = """
    <Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
            xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
            WindowStyle="None" Background="{x:Null}"
            ShowInTaskbar="False" ShowActivated="False"
            WindowStartupLocation="Manual" ResizeMode="NoResize" Topmost="True"
            ScrollViewer.VerticalScrollBarVisibility="Disabled">
        <Grid Background="#FFEA9F00">
            <TextBlock x:Name="message_tb"
                       TextWrapping="Wrap" Text="TextBlock"
                       TextAlignment="Center" VerticalAlignment="Center"
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


def alert(msg, title='pyRevit', cancel=False, yes=False, no=False, retry=False):
    buttons = UI.TaskDialogCommonButtons.Ok

    if any([cancel, yes, no, retry]):
        buttons = UI.TaskDialogCommonButtons.None

        if cancel:
            buttons |= UI.TaskDialogCommonButtons.Cancel
        if yes:
            buttons |= UI.TaskDialogCommonButtons.Yes
        if no:
            buttons |= UI.TaskDialogCommonButtons.No
        if retry:
            buttons |= UI.TaskDialogCommonButtons.Retry

    res = UI.TaskDialog.Show(title, msg, buttons)

    if res == UI.TaskDialogResult.Ok \
        or res == UI.TaskDialogResult.Yes \
        or res == UI.TaskDialogResult.Retry:
        return True
    else:
        return False
