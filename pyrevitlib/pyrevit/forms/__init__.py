import os
import os.path as op

from pyrevit import HOST_APP, EXEC_PARAMS
from pyrevit import coreutils
from pyrevit.coreutils.logger import get_logger
from pyrevit import framework
from pyrevit.framework import System
from pyrevit.framework import Threading
from pyrevit.framework import Interop
from pyrevit.framework import wpf, Forms, Controls, Media
from pyrevit.api import AdWindows
from pyrevit import revit, UI, DB


logger = get_logger(__name__)


class WPFWindow(framework.Windows.Window):
    def __init__(self, xaml_file, literal_string=False):
        # self.Parent = self
        wih = Interop.WindowInteropHelper(self)
        wih.Owner = AdWindows.ComponentManager.ApplicationWindow

        if not literal_string:
            if not op.exists(xaml_file):
                wpf.LoadComponent(self,
                                  os.path.join(EXEC_PARAMS.command_path,
                                               xaml_file)
                                  )
            else:
                wpf.LoadComponent(self, xaml_file)
        else:
            wpf.LoadComponent(self, framework.StringReader(xaml_file))

    def show(self):
        return self.Show()

    def show_dialog(self):
        return self.ShowDialog()

    def set_image_source(self, element_name, image_file):
        wpf_element = getattr(self, element_name)
        if not op.exists(image_file):
            # noinspection PyUnresolvedReferences
            wpf_element.Source = \
                framework.Imaging.BitmapImage(
                    framework.Uri(os.path.join(EXEC_PARAMS.command_path,
                                               image_file))
                    )
        else:
            wpf_element.Source = \
                framework.Imaging.BitmapImage(framework.Uri(image_file))

    @staticmethod
    def hide_element(*wpf_elements):
        for wpf_element in wpf_elements:
            wpf_element.Visibility = framework.Windows.Visibility.Collapsed

    @staticmethod
    def show_element(*wpf_elements):
        for wpf_element in wpf_elements:
            wpf_element.Visibility = framework.Windows.Visibility.Visible


class TemplateUserInputWindow(WPFWindow):
    layout = """
    <Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
            xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
            ShowInTaskbar="False" ResizeMode="NoResize"
            WindowStartupLocation="CenterScreen"
            HorizontalContentAlignment="Center">
    </Window>
    """

    def __init__(self, context, title, width, height, **kwargs):
        WPFWindow.__init__(self, self.layout, literal_string=True)
        self.Title = title
        self.Width = width
        self.Height = height

        self._context = context
        self.response = None
        self.PreviewKeyDown += self.handle_esc_key

        self._setup(**kwargs)

    def _setup(self, **kwargs):
        pass

    def handle_esc_key(self, sender, args):
        if args.Key == framework.Windows.Input.Key.Escape:
            self.Close()

    @classmethod
    def show(cls, context,
             title='User Input', width=300, height=400, **kwargs):
        dlg = cls(context, title, width, height, **kwargs)
        dlg.ShowDialog()
        return dlg.response


class SelectFromList(TemplateUserInputWindow):
    layout = """
    <Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
            xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
            ShowInTaskbar="False" ResizeMode="NoResize"
            WindowStartupLocation="CenterScreen"
            HorizontalContentAlignment="Center">
            <Window.Resources>
                <Style x:Key="ClearButton" TargetType="Button">
                    <Setter Property="Background" Value="White"/>
                </Style>
            </Window.Resources>
            <DockPanel Margin="10">
                <DockPanel DockPanel.Dock="Top" Margin="0,0,0,10">
                    <TextBlock FontSize="14" Margin="0,3,10,0"
                               DockPanel.Dock="Left">
                               Filter:
                    </TextBlock>
                    <StackPanel>
                        <TextBox x:Name="search_tb" Height="25px"
                                 TextChanged="search_txt_changed"/>
                        <Button Style="{StaticResource ClearButton}"
                                HorizontalAlignment="Right"
                                x:Name="clrsearch_b" Content="x"
                                Margin="0,-25,5,0" Padding="0,-4,0,0"
                                Click="clear_search"
                                Width="15px" Height="15px"/>
                    </StackPanel>
                </DockPanel>
                <Button x:Name="select_b"
                        Content="Select" Click="button_select"
                        DockPanel.Dock="Bottom" Margin="0,10,0,0"/>
                <ListView x:Name="list_lb" />
            </DockPanel>
    </Window>
    """

    def _setup(self, **kwargs):
        self.hide_element(self.clrsearch_b)
        self.clear_search(None, None)
        self.search_tb.Focus()

        if 'multiselect' in kwargs and not kwargs['multiselect']:
            self.list_lb.SelectionMode = Controls.SelectionMode.Single
        else:
            self.list_lb.SelectionMode = Controls.SelectionMode.Extended

        self.select_b.Content = kwargs.get('button_name', '')

        self._list_options()

    def _list_options(self, option_filter=None):
        if option_filter:
            option_filter = option_filter.lower()
            self.list_lb.ItemsSource = \
                [str(option) for option in self._context
                 if option_filter in str(option).lower()]
        else:
            self.list_lb.ItemsSource = \
                [str(option) for option in self._context]

    def _get_options(self):
        return [option for option in self._context
                if str(option) in self.list_lb.SelectedItems]

    def button_select(self, sender, args):
        self.response = self._get_options()
        self.Close()

    def search_txt_changed(self, sender, args):
        if self.search_tb.Text == '':
            self.hide_element(self.clrsearch_b)
        else:
            self.show_element(self.clrsearch_b)

        self._list_options(option_filter=self.search_tb.Text)

    def clear_search(self, sender, args):
        self.search_tb.Text = ' '
        self.search_tb.Clear()
        self.list_lb.ItemsSource = self._context


class SelectFromCheckBoxes(TemplateUserInputWindow):
    layout = """
    <Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
            xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
            ShowInTaskbar="False" ResizeMode="NoResize"
            WindowStartupLocation="CenterScreen"
            HorizontalContentAlignment="Center">
            <Window.Resources>
                <Style x:Key="ClearButton" TargetType="Button">
                    <Setter Property="Background" Value="White"/>
                </Style>
            </Window.Resources>
            <DockPanel Margin="10">
                <DockPanel DockPanel.Dock="Top" Margin="0,0,0,10">
                    <TextBlock FontSize="14" Margin="0,3,10,0" \
                               DockPanel.Dock="Left">Filter:</TextBlock>
                    <StackPanel>
                        <TextBox x:Name="search_tb" Height="25px"
                                 TextChanged="search_txt_changed"/>
                        <Button Style="{StaticResource ClearButton}"
                                HorizontalAlignment="Right"
                                x:Name="clrsearch_b" Content="x"
                                Margin="0,-25,5,0" Padding="0,-4,0,0"
                                Click="clear_search"
                                Width="15px" Height="15px"/>
                    </StackPanel>
                </DockPanel>
                <StackPanel DockPanel.Dock="Bottom">
                    <Grid>
                        <Grid.RowDefinitions>
                            <RowDefinition Height="Auto" />
                        </Grid.RowDefinitions>
                        <Grid.ColumnDefinitions>
                            <ColumnDefinition Width="*" />
                            <ColumnDefinition Width="*" />
                            <ColumnDefinition Width="*" />
                        </Grid.ColumnDefinitions>
                        <Button x:Name="checkall_b"
                                Grid.Column="0" Grid.Row="0"
                                Content="Check" Click="check_all"
                                Margin="0,10,3,0"/>
                        <Button x:Name="uncheckall_b"
                                Grid.Column="1" Grid.Row="0"
                                Content="Uncheck" Click="uncheck_all"
                                Margin="3,10,3,0"/>
                        <Button x:Name="toggleall_b"
                                Grid.Column="2" Grid.Row="0"
                                Content="Toggle" Click="toggle_all"
                                Margin="3,10,0,0"/>
                    </Grid>
                    <Button x:Name="select_b" Content=""
                            Click="button_select" Margin="0,10,0,0"/>
                </StackPanel>
                <ListView x:Name="list_lb">
                    <ListView.ItemTemplate>
                         <DataTemplate>
                           <StackPanel>
                             <CheckBox Content="{Binding name}"
                                       IsChecked="{Binding state}"/>
                           </StackPanel>
                         </DataTemplate>
                   </ListView.ItemTemplate>
                </ListView>
            </DockPanel>
    </Window>
    """

    def _setup(self, **kwargs):
        self.hide_element(self.clrsearch_b)
        self.clear_search(None, None)
        self.search_tb.Focus()

        if 'button_name' in kwargs:
            self.select_b.Content = kwargs['button_name']

        self._list_options()

    def _list_options(self, checkbox_filter=None):
        if checkbox_filter:
            self.checkall_b.Content = 'Check'
            self.uncheckall_b.Content = 'Uncheck'
            self.toggleall_b.Content = 'Toggle'
            checkbox_filter = checkbox_filter.lower()
            self.list_lb.ItemsSource = \
                [checkbox for checkbox in self._context
                 if checkbox_filter in checkbox.name.lower()]
        else:
            self.checkall_b.Content = 'Check All'
            self.uncheckall_b.Content = 'Uncheck All'
            self.toggleall_b.Content = 'Toggle All'
            self.list_lb.ItemsSource = self._context

    def _set_states(self, state=True, flip=False):
        current_list = self.list_lb.ItemsSource
        for checkbox in current_list:
            if flip:
                checkbox.state = not checkbox.state
            else:
                checkbox.state = state

        # push list view to redraw
        self.list_lb.ItemsSource = None
        self.list_lb.ItemsSource = current_list

    def toggle_all(self, sender, args):
        self._set_states(flip=True)

    def check_all(self, sender, args):
        self._set_states(state=True)

    def uncheck_all(self, sender, args):
        self._set_states(state=False)

    def button_select(self, sender, args):
        self.response = self._context
        self.Close()

    def search_txt_changed(self, sender, args):
        if self.search_tb.Text == '':
            self.hide_element(self.clrsearch_b)
        else:
            self.show_element(self.clrsearch_b)

        self._list_options(checkbox_filter=self.search_tb.Text)

    def clear_search(self, sender, args):
        self.search_tb.Text = ' '
        self.search_tb.Clear()
        self.list_lb.ItemsSource = self._context


class CommandSwitchWindow(TemplateUserInputWindow):
    layout = """
    <Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
            xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
            ShowInTaskbar="False" ResizeMode="NoResize"
            WindowStartupLocation="CenterScreen"
            HorizontalContentAlignment="Center"
            WindowStyle="None"
            AllowsTransparency="True"
            Background="#00FFFFFF"
            SizeToContent="Height"
            PreviewKeyDown="handle_esc_key"
            MouseUp="handle_click">
        <Window.Resources>
            <Style TargetType="Button">
                <Setter Property="FocusVisualStyle" Value="{x:Null}"/>
                    <Setter Property="Background" Value="#ffffff"/>
                    <Setter Property="BorderBrush" Value="#cccccc"/>
                    <Setter Property="BorderThickness" Value="0"/>
                    <Setter Property="Foreground" Value="#23303d"/>
                    <Setter Property="HorizontalContentAlignment" Value="Center"/>
                    <Setter Property="VerticalContentAlignment" Value="Center"/>
                    <Setter Property="Padding" Value="10,2,10,2"/>
                    <Setter Property="Template">
                        <Setter.Value>
                            <ControlTemplate TargetType="{x:Type Button}">
                                <Border Name="Chrome"
                                        Background="{TemplateBinding Background}"
                                        BorderBrush="{TemplateBinding BorderBrush}"
                                        BorderThickness="{TemplateBinding BorderThickness}"
                                        CornerRadius="10"
                                        Height="20"
                                        Margin="0,0,5,5"
                                        SnapsToDevicePixels="true">
                                    <ContentPresenter Name="Presenter"
                                                      Margin="{TemplateBinding Padding}"
                                                      VerticalAlignment="{TemplateBinding VerticalContentAlignment}"
                                                      HorizontalAlignment="{TemplateBinding HorizontalContentAlignment}"
                                                      RecognizesAccessKey="True"
                                                      SnapsToDevicePixels="{TemplateBinding SnapsToDevicePixels}"/>
                                </Border>
                                <ControlTemplate.Triggers>
                                    <Trigger Property="IsEnabled" Value="false">
                                        <Setter Property="Foreground" Value="#23303d" />
                                    </Trigger>
                                    <Trigger Property="IsMouseOver" Value="True">
                                        <Setter Property="Background" Value="#f39c12" />
                                        <Setter Property="BorderBrush" Value="#f39c12" />
                                        <Setter Property="Foreground" Value="White" />
                                    </Trigger>
                                    <Trigger Property="IsPressed" Value="True">
                                        <Setter Property="Background" Value="#f39c12" />
                                        <Setter Property="BorderBrush" Value="#f39c12"/>
                                        <Setter Property="Foreground" Value="#ffffff"/>
                                    </Trigger>
                                    <Trigger Property="IsFocused" Value="true">
                                        <Setter TargetName="Chrome" Property="BorderBrush" Value="#1ba1e2" />
                                    </Trigger>
                                </ControlTemplate.Triggers>
                            </ControlTemplate>
                        </Setter.Value>
                    </Setter>
            </Style>
        </Window.Resources>
        <Border CornerRadius="15"
                Background="#f323303d">
            <StackPanel x:Name="stack_panel" Margin="5">
                <Label x:Name="message_label"
                       Foreground="White"
                       Margin="2,0,0,0" />
                <WrapPanel x:Name="button_list" Margin="5" />
            </StackPanel>
        </Border>
    </Window>
    """

    def _setup(self, **kwargs):
        self.selected_switch = ''
        self.Width = 600
        self.Title = 'Command Options'

        message = kwargs.get('message', None)

        self.message_label.Content = \
            message if message else 'Pick a command option:'

        for switch in self._context:
            my_button = framework.Controls.Button()
            my_button.Content = switch
            my_button.Click += self.process_switch
            self.button_list.Children.Add(my_button)

    def handle_click(self, sender, args):
        self.Close()

    def process_switch(self, sender, args):
        self.Close()
        self.response = sender.Content


class TemplatePromptBar(WPFWindow):
    layout = """
    <Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
            xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
            WindowStyle="None" Background="{x:Null}"
            ShowInTaskbar="False" ShowActivated="False"
            WindowStartupLocation="Manual"
            ResizeMode="NoResize"
            ScrollViewer.VerticalScrollBarVisibility="Disabled">
        <Grid>
        </Grid>
    </Window>
    """

    def __init__(self, height=32, **kwargs):
        WPFWindow.__init__(self, self.layout, literal_string=True)

        self.user_height = height
        self.update_window()

        self._setup(**kwargs)

    def update_window(self):
        scale_factor = 1 / HOST_APP.proc_screen_scalefactor

        window_rect = revit.get_window_rectangle()

        top = left = width = height = 0

        width = (window_rect.Right - window_rect.Left) * scale_factor
        height = self.user_height

        top = window_rect.Top * scale_factor
        # in maximized window, the top will be off the screen (- value)
        # lets cut the height and re-adjust the top
        if top < 0:
            height -= abs(top)
            top = 0

        left = window_rect.Left * scale_factor
        # Left also might be off screen, let's fix that as well
        if left < 0:
            width -= abs(left)
            left = 0

        self.Top, self.Left, self.Width, self.Height = top, left, width, height

    def _setup(self, **kwargs):
        pass

    def __enter__(self):
        self.Show()
        return self

    def __exit__(self, exception, exception_value, traceback):
        self.Close()


class WarningBar(TemplatePromptBar):
    layout = """
    <Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
            xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
            WindowStyle="None" Background="{x:Null}"
            ShowInTaskbar="False" ShowActivated="False"
            WindowStartupLocation="Manual"
            ResizeMode="NoResize"
            ScrollViewer.VerticalScrollBarVisibility="Disabled">
        <Grid Background="#FFEA9F00">
            <TextBlock x:Name="message_tb"
                       TextWrapping="Wrap"
                       Text="TextBlock"
                       TextAlignment="Center"
                       VerticalAlignment="Center"
                       FontWeight="Bold"
                       Foreground="{DynamicResource {x:Static SystemColors.WindowBrushKey}}"/>
        </Grid>
    </Window>
    """

    def _setup(self, **kwargs):
        self.message_tb.Text = kwargs.get('title', '')


class ProgressBar(TemplatePromptBar):
    layout = """
    <Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
                xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
                WindowStyle="None" Background="{x:Null}"
                ShowInTaskbar="False" ShowActivated="False"
                WindowStartupLocation="Manual"
                ResizeMode="NoResize"
                ScrollViewer.VerticalScrollBarVisibility="Disabled">
        <Window.Resources>
            <Style TargetType="Button">
                <Setter Property="FocusVisualStyle" Value="{x:Null}"/>
                    <Setter Property="Background" Value="#ffffff"/>
                    <Setter Property="BorderBrush" Value="#cccccc"/>
                    <Setter Property="BorderThickness" Value="0"/>
                    <Setter Property="Foreground" Value="#23303d"/>
                    <Setter Property="HorizontalContentAlignment" Value="Center"/>
                    <Setter Property="VerticalContentAlignment" Value="Center"/>
                    <Setter Property="Padding" Value="8,2,8,2"/>
                    <Setter Property="Template">
                        <Setter.Value>
                            <ControlTemplate TargetType="{x:Type Button}">
                                <Border Name="Chrome"
                                        Background="{TemplateBinding Background}"
                                        BorderBrush="{TemplateBinding BorderBrush}"
                                        BorderThickness="{TemplateBinding BorderThickness}"
                                        CornerRadius="10"
                                        SnapsToDevicePixels="true">
                                    <ContentPresenter Name="Presenter"
                                                      Margin="{TemplateBinding Padding}"
                                                      VerticalAlignment="{TemplateBinding VerticalContentAlignment}"
                                                      HorizontalAlignment="{TemplateBinding HorizontalContentAlignment}"
                                                      RecognizesAccessKey="True"
                                                      SnapsToDevicePixels="{TemplateBinding SnapsToDevicePixels}"/>
                                </Border>
                                <ControlTemplate.Triggers>
                                    <Trigger Property="IsEnabled" Value="false">
                                        <Setter Property="Foreground" Value="#23303d" />
                                    </Trigger>
                                    <Trigger Property="IsMouseOver" Value="True">
                                        <Setter Property="Background" Value="#dddddd" />
                                        <Setter Property="BorderBrush" Value="#cccccc" />
                                        <Setter Property="Foreground" Value="#23303d" />
                                    </Trigger>
                                    <Trigger Property="IsPressed" Value="True">
                                        <Setter Property="Background" Value="#f39c12" />
                                        <Setter Property="BorderBrush" Value="#f39c12"/>
                                        <Setter Property="Foreground" Value="#ffffff"/>
                                    </Trigger>
                                    <Trigger Property="IsFocused" Value="true">
                                        <Setter TargetName="Chrome" Property="BorderBrush" Value="#1ba1e2" />
                                    </Trigger>
                                </ControlTemplate.Triggers>
                            </ControlTemplate>
                        </Setter.Value>
                    </Setter>
            </Style>
            <Style x:Key="{x:Type ProgressBar}" TargetType="{x:Type ProgressBar}">
                <Setter Property="Template">
                    <Setter.Value>
                        <ControlTemplate TargetType="{x:Type ProgressBar}">
                            <Grid>
                                <VisualStateManager.VisualStateGroups>
                                    <VisualStateGroup x:Name="CommonStates">
                                        <VisualState x:Name="Determinate" />
                                        <VisualState x:Name="Indeterminate">
                                            <Storyboard>
                                                <ObjectAnimationUsingKeyFrames Duration="00:00:00" Storyboard.TargetName="PART_Indicator" Storyboard.TargetProperty="Background">
                                                    <DiscreteObjectKeyFrame KeyTime="00:00:00" />
                                                </ObjectAnimationUsingKeyFrames>
                                            </Storyboard>
                                        </VisualState>
                                    </VisualStateGroup>
                                </VisualStateManager.VisualStateGroups>
                                <Border x:Name="PART_Track" CornerRadius="0" BorderThickness="0" />
                                <Border x:Name="PART_Indicator" CornerRadius="0" BorderThickness="0" HorizontalAlignment="Left" Background="#FFEA9F00" Margin="0">
                                    <Grid ClipToBounds="True" x:Name="Animation">
                                        <Border x:Name="PART_GlowRect" Width="200" HorizontalAlignment="Left" Background="#FFEA9F00" Margin="-200,0,0,0" />
                                    </Grid>
                                </Border>
                            </Grid>
                        </ControlTemplate>
                    </Setter.Value>
                </Setter>
                <Setter Property="Background">
                    <Setter.Value>
                        <SolidColorBrush Color="#FFF0F0F0" />
                    </Setter.Value>
                </Setter>
                <Setter Property="Foreground">
                    <Setter.Value>
                        <SolidColorBrush Color="#FFEA9F00" />
                    </Setter.Value>
                </Setter>
            </Style>
        </Window.Resources>
        <Grid Background="#ff2c3e50">
            <ProgressBar x:Name="pbar"/>
            <TextBlock x:Name="pbar_text"
                       TextWrapping="Wrap" Text="TextBlock"
                       TextAlignment="Center" VerticalAlignment="Center"
                       Foreground="{DynamicResource {x:Static SystemColors.WindowBrushKey}}"/>
            <Button HorizontalAlignment="Left"
                    VerticalAlignment="Center"
                    Content="Cancel"
                    Margin="12,0,0,0"
                    Padding="10,0,10,0"
                    Click="clicked_cancel"
                    Height="18px" />
        </Grid>
    </Window>
    """

    def _setup(self, **kwargs):
        self.cancelled = False
        self.pbar.IsIndeterminate = kwargs.get('indeterminate', False)

    def _update_pbar(self):
        self.update_window()
        self.pbar.Maximum = self.max_value
        self.pbar.Value = self.new_value
        self.pbar_text.Text = '{} / {}'.format(self.new_value, self.max_value)

    def clicked_cancel(self, sender, args):
        self.cancelled = True

    def update_progress(self, new_value, max_value):
        self.max_value = max_value
        self.new_value = new_value
        self.pbar.Dispatcher.Invoke(System.Action(self._update_pbar),
                                    Threading.DispatcherPriority.Background)


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


def pick_folder():
    fb_dlg = Forms.FolderBrowserDialog()
    if fb_dlg.ShowDialog() == Forms.DialogResult.OK:
        return fb_dlg.SelectedPath


def pick_file(file_ext='', files_filter='', init_dir='',
              restore_dir=True, multi_file=False, unc_paths=False):
    of_dlg = Forms.OpenFileDialog()
    if files_filter:
        of_dlg.Filter = files_filter
    else:
        of_dlg.Filter = '|*.{}'.format(file_ext)
    of_dlg.RestoreDirectory = restore_dir
    of_dlg.Multiselect = multi_file
    if init_dir:
        of_dlg.InitialDirectory = init_dir
    if of_dlg.ShowDialog() == Forms.DialogResult.OK:
        if unc_paths:
            return coreutils.dletter_to_unc(of_dlg.FileName)
        return of_dlg.FileName


def save_file(file_ext='', files_filter='', init_dir='', default_name='',
              restore_dir=True, unc_paths=False):
    sf_dlg = Forms.SaveFileDialog()
    if files_filter:
        sf_dlg.Filter = files_filter
    else:
        sf_dlg.Filter = '|*.{}'.format(file_ext)
    sf_dlg.RestoreDirectory = restore_dir
    if init_dir:
        sf_dlg.InitialDirectory = init_dir

    # setting default filename
    sf_dlg.FileName = default_name

    if sf_dlg.ShowDialog() == Forms.DialogResult.OK:
        if unc_paths:
            return coreutils.dletter_to_unc(sf_dlg.FileName)
        return sf_dlg.FileName


class RevisionOption(object):
    def __init__(self, revision_element):
        self.revision_element = revision_element

    def __str__(self):
        return '{}-{}-{}'.format(self.revision_element.RevisionNumber,
                                 self.revision_element.Description,
                                 self.revision_element.RevisionDate)


class SheetOption(object):
    def __init__(self, sheet_element):
        self.state = False
        self.sheet_element = sheet_element
        self.name = '{} - {}'.format(self.sheet_element.SheetNumber,
                                     self.sheet_element.Name)
        self.number = self.sheet_element.SheetNumber

    def __nonzero__(self):
        return self.state


def select_revisions(title='Select Revision',
                     button_name='Select',
                     width=300,
                     multiselect=True):
    unsorted_revisions = \
        DB.FilteredElementCollector(revit.doc)\
          .OfCategory(DB.BuiltInCategory.OST_Revisions)\
          .WhereElementIsNotElementType()

    revisions = sorted(unsorted_revisions, key=lambda x: x.RevisionNumber)
    revision_options = [RevisionOption(x) for x in revisions]

    # ask user for revisions
    return_options = \
        SelectFromList.show(
            revision_options,
            title=title,
            button_name=button_name,
            width=width,
            multiselect=multiselect
            )

    if return_options:
        if not multiselect and len(return_options) == 1:
            return return_options[0].revision_element
        else:
            return [x.revision_element for x in return_options]


def select_sheets(title='Select Sheets', button_name='Select', width=300):
    all_sheets = DB.FilteredElementCollector(revit.doc) \
                   .OfClass(DB.ViewSheet) \
                   .WhereElementIsNotElementType() \
                   .ToElements()

    # ask user for sheets
    return_options = \
        SelectFromCheckBoxes.show(
            sorted([SheetOption(x) for x in all_sheets],
                   key=lambda x: x.number),
            title=title,
            button_name=button_name,
            width=width,)

    if return_options:
        return [x.sheet_element for x in return_options if x.state]
