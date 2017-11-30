import os
import os.path as op
import string
from collections import OrderedDict

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
    def __init__(self, xaml_source, literal_string=False):
        # self.Parent = self
        wih = Interop.WindowInteropHelper(self)
        wih.Owner = AdWindows.ComponentManager.ApplicationWindow

        if not literal_string:
            if not op.exists(xaml_source):
                wpf.LoadComponent(self,
                                  os.path.join(EXEC_PARAMS.command_path,
                                               xaml_source)
                                  )
            else:
                wpf.LoadComponent(self, xaml_source)
        else:
            wpf.LoadComponent(self, framework.StringReader(xaml_source))

        #2c3e50
        self.Resources['pyRevitDarkColor'] = \
            Media.Color.FromArgb(0xFF, 0x2c, 0x3e, 0x50)

        #23303d
        self.Resources['pyRevitDarkerDarkColor'] = \
            Media.Color.FromArgb(0xFF, 0x23, 0x30, 0x3d)

        #ffffff
        self.Resources['pyRevitButtonColor'] = \
            Media.Color.FromArgb(0xFF, 0xff, 0xff, 0xff)

        #f39c12
        self.Resources['pyRevitAccentColor'] = \
            Media.Color.FromArgb(0xFF, 0xf3, 0x9c, 0x12)

        self.Resources['pyRevitDarkBrush'] = \
            Media.SolidColorBrush(self.Resources['pyRevitDarkColor'])
        self.Resources['pyRevitAccentBrush'] = \
            Media.SolidColorBrush(self.Resources['pyRevitAccentColor'])

        self.Resources['pyRevitDarkerDarkBrush'] = \
            Media.SolidColorBrush(self.Resources['pyRevitDarkerDarkColor'])

        self.Resources['pyRevitButtonForgroundBrush'] = \
            Media.SolidColorBrush(self.Resources['pyRevitButtonColor'])

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
        self.PreviewKeyDown += self.handle_input_key

        self._setup(**kwargs)

    def _setup(self, **kwargs):
        pass

    def handle_input_key(self, sender, args):
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
            MouseUp="handle_click">
        <Window.Resources>
            <Style TargetType="{x:Type Button}">
                <Setter Property="FocusVisualStyle" Value="{x:Null}"/>
                    <Setter Property="Background" Value="#ffffff"/>
                    <Setter Property="BorderBrush" Value="#cccccc"/>
                    <Setter Property="BorderThickness" Value="0"/>
                    <Setter Property="Foreground" Value="{DynamicResource pyRevitDarkerDarkBrush}"/>
                    <Setter Property="HorizontalContentAlignment" Value="Center"/>
                    <Setter Property="VerticalContentAlignment" Value="Center"/>
                    <Setter Property="Padding" Value="10,2,10,2"/>
                    <Setter Property="Template">
                        <Setter.Value>
                            <ControlTemplate TargetType="{x:Type Button}">
                                <Border Background="{TemplateBinding Background}"
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
                                        <Setter Property="Foreground" Value="{DynamicResource pyRevitDarkerDarkBrush}" />
                                    </Trigger>
                                    <Trigger Property="IsMouseOver" Value="True">
                                        <Setter Property="Background" Value="{DynamicResource pyRevitAccentBrush}" />
                                        <Setter Property="BorderBrush" Value="{DynamicResource pyRevitAccentBrush}" />
                                        <Setter Property="Foreground" Value="White" />
                                    </Trigger>
                                    <Trigger Property="IsPressed" Value="True">
                                        <Setter Property="Background" Value="{DynamicResource pyRevitAccentBrush}" />
                                        <Setter Property="BorderBrush" Value="{DynamicResource pyRevitAccentBrush}"/>
                                        <Setter Property="Foreground" Value="{DynamicResource pyRevitButtonForgroundBrush}"/>
                                    </Trigger>
                                    <Trigger Property="IsFocused" Value="true">
                                        <Setter Property="Background" Value="{DynamicResource pyRevitAccentBrush}" />
                                        <Setter Property="BorderBrush" Value="{DynamicResource pyRevitAccentBrush}" />
                                        <Setter Property="Foreground" Value="White" />
                                    </Trigger>
                                </ControlTemplate.Triggers>
                            </ControlTemplate>
                        </Setter.Value>
                    </Setter>
            </Style>
            <Style TargetType="{x:Type TextBox}">
                <Setter Property="SnapsToDevicePixels" Value="True"/>
                <Setter Property="OverridesDefaultStyle" Value="True"/>
                <Setter Property="FocusVisualStyle" Value="{x:Null}"/>
                <Setter Property="AllowDrop" Value="False"/>
                <Setter Property="Foreground" Value="White"/>
                <Setter Property="CaretBrush" Value="#00000000"/>
                <Setter Property="Template">
                    <Setter.Value>
                        <ControlTemplate TargetType="{x:Type TextBoxBase}">
                            <Border Name="Border"
                                    Padding="2"
                                    CornerRadius="10"
                                    Background="{x:Null}"
                                    BorderBrush="#66ffffff"
                                    BorderThickness="1" >
                                <Grid Margin="5,0,5,0">
                                    <ScrollViewer Margin="0" x:Name="PART_ContentHost"/>
                                    <TextBlock Text="{TemplateBinding Tag}"
                                               Foreground="#66ffffff"/>
                                </Grid>
                            </Border>
                            <ControlTemplate.Triggers>
                                <Trigger Property="IsEnabled" Value="False">
                                    <Setter TargetName="Border" Property="Background" Value="{x:Null}"/>
                                    <Setter TargetName="Border" Property="BorderBrush" Value="{x:Null}"/>
                                </Trigger>
                            </ControlTemplate.Triggers>
                        </ControlTemplate>
                    </Setter.Value>
                </Setter>
            </Style>
        <Style TargetType="{x:Type ToggleButton}">
            <Setter Property="FocusVisualStyle" Value="{x:Null}"/>
            <Setter Property="Foreground" Value="{DynamicResource pyRevitDarkBrush}" />
            <Setter Property="Background" Value="White" />
            <Setter Property="BorderBrush" Value="#CCCCCC" />
            <Setter Property="Template">
                <Setter.Value>
                    <ControlTemplate TargetType="ToggleButton">
                        <Border Background="{TemplateBinding Background}"
                                    HorizontalAlignment="Center"
                                    Padding="6,0,10,0"
                                    CornerRadius="10"
                                    Height="20"
                                    Margin="0,0,5,5"
                                    SnapsToDevicePixels="true">
                            <StackPanel Orientation="Horizontal"
                                            HorizontalAlignment="Center">
                                <Canvas Name="Layer_1"
                                            Width="25"
                                            Height="12"
                                            VerticalAlignment="Center">
                                    <Line Canvas.Top="6"
                                              X1="5" X2="20"
                                              Width="25"
                                              StrokeThickness="1"
                                              Stroke="{TemplateBinding BorderBrush}"/>
                                    <Ellipse x:Name="ellipse"
                                                 Canvas.Left="0"
                                                 Width="12"
                                                 Height="12"
                                                 Fill="White"
                                                 Stroke="{TemplateBinding BorderBrush}"
                                                 StrokeThickness="1">
                                        <Ellipse.RenderTransform>
                                            <TranslateTransform X="0" Y="0" />
                                        </Ellipse.RenderTransform>
                                    </Ellipse>
                                </Canvas>
                                <TextBlock x:Name="buttontitle"
                                               Text="{TemplateBinding Content}"
                                               Margin="5,0,5,0"
                                               Height="{TemplateBinding Height}"
                                               VerticalAlignment="Center"
                                               Foreground="{TemplateBinding Foreground}"/>
                            </StackPanel>
                        </Border>
                        <ControlTemplate.Triggers>
                            <Trigger Property="IsChecked" Value="True" >
                                <Trigger.EnterActions>
                                    <BeginStoryboard>
                                        <Storyboard>
                                            <ColorAnimation Storyboard.TargetName="ellipse" Storyboard.TargetProperty="Fill.Color" To="#2c3e50" Duration="0:0:0.1" />
                                            <DoubleAnimationUsingKeyFrames Storyboard.TargetProperty="(Ellipse.RenderTransform).(TranslateTransform.X)"
                                                                           Storyboard.TargetName="ellipse">
                                                <SplineDoubleKeyFrame KeyTime="0" Value="0"/>
                                                <SplineDoubleKeyFrame KeyTime="0:0:0.1" Value="15"/>
                                            </DoubleAnimationUsingKeyFrames>
                                        </Storyboard>
                                    </BeginStoryboard>
                                </Trigger.EnterActions>
                                <Trigger.ExitActions>
                                    <BeginStoryboard>
                                        <Storyboard>
                                            <ColorAnimation Storyboard.TargetName="ellipse" Storyboard.TargetProperty="Fill.Color" To="White" Duration="0:0:0.1" />
                                            <DoubleAnimationUsingKeyFrames Storyboard.TargetProperty="(Ellipse.RenderTransform).(TranslateTransform.X)"
                                                                               Storyboard.TargetName="ellipse">
                                                <SplineDoubleKeyFrame KeyTime="0" Value="15"/>
                                                <SplineDoubleKeyFrame KeyTime="0:0:0.1" Value="0"/>
                                            </DoubleAnimationUsingKeyFrames>
                                        </Storyboard>
                                    </BeginStoryboard>
                                </Trigger.ExitActions>
                            </Trigger>
                            <Trigger Property="IsFocused" Value="true">
                                <Setter Property="Background" Value="{DynamicResource pyRevitAccentBrush}" />
                                <Setter Property="Foreground" Value="White" />
                            </Trigger>
                        </ControlTemplate.Triggers>
                    </ControlTemplate>
                </Setter.Value>
            </Setter>
        </Style>
        </Window.Resources>
        <Border CornerRadius="15"
                Background="{DynamicResource pyRevitDarkerDarkBrush}">
            <StackPanel x:Name="stack_panel" Margin="10">
                <DockPanel Height="36">
                    <Label x:Name="message_label"
                           VerticalAlignment="Center"
                           DockPanel.Dock="Left"
                           FontSize="14"
                           Foreground="White" />
                    <TextBox x:Name="search_tb"
                             Margin="10,2,5,0"
                             VerticalAlignment="Center"
                             TextChanged="search_txt_changed"/>
                </DockPanel>
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
        self._switches = kwargs.get('switches', [])

        self.message_label.Content = \
            message if message else 'Pick a command option:'

        # creates the switches first
        for switch in self._switches:
            my_togglebutton = framework.Controls.Primitives.ToggleButton()
            my_togglebutton.Content = switch
            self.button_list.Children.Add(my_togglebutton)

        for option in self._context:
            my_button = framework.Controls.Button()
            my_button.Content = option
            my_button.Click += self.process_option
            self.button_list.Children.Add(my_button)

        self._setup_response()
        self.search_tb.Focus()
        self._filter_options()

    def _setup_response(self, response=None):
        if self._switches:
            switches = [x for x in self.button_list.Children
                        if hasattr(x, 'IsChecked')]
            self.response = response, {x.Content: x.IsChecked
                                       for x in switches}
        else:
            self.response = response

    def _filter_options(self, option_filter=None):
        if option_filter:
            self.search_tb.Tag = ''
            option_filter = option_filter.lower()
            for button in self.button_list.Children:
                if option_filter not in button.Content.lower():
                    button.Visibility = framework.Windows.Visibility.Collapsed
                else:
                    button.Visibility = framework.Windows.Visibility.Visible
        else:
            self.search_tb.Tag = 'Type to Filter / Tab to Select / Enter to Run'
            for button in self.button_list.Children:
                button.Visibility = framework.Windows.Visibility.Visible

    def _get_active_button(self):
        buttons = []
        for button in self.button_list.Children:
            if button.Visibility == framework.Windows.Visibility.Visible:
                buttons.append(button)
        if len(buttons) == 1:
            return buttons[0]
        else:
            return [x for x in buttons if x.IsFocused][0]

    def handle_click(self, sender, args):
        self.Close()

    def handle_input_key(self, sender, args):
        if args.Key == framework.Windows.Input.Key.Escape:
            if self.search_tb.Text:
                self.search_tb.Text = ''
            else:
                self.Close()
        elif args.Key == framework.Windows.Input.Key.Enter:
            self.process_option(self._get_active_button(), None)
        elif args.Key != framework.Windows.Input.Key.Tab \
                and args.Key != framework.Windows.Input.Key.Space:
            self.search_tb.Focus()

    def search_txt_changed(self, sender, args):
        self._filter_options(option_filter=self.search_tb.Text)

    def process_option(self, sender, args):
        self.Close()
        self._setup_response(response=sender.Content)


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

        width = window_rect.Right - window_rect.Left
        height = self.user_height


        top = window_rect.Top
        # in maximized window, the top will be off the screen (- value)
        # lets cut the height and re-adjust the top
        if top < 0:
            height -= abs(top)
            top = 0

        left = window_rect.Left
        # Left also might be off screen, let's fix that as well
        if left < 0:
            # deduct two times the left negative offset since this extra offset
            # is on both sides
            width -= abs(left * 2)
            left = 0

        self.Top = top * scale_factor
        self.Left = left * scale_factor
        self.Width = width * scale_factor
        self.Height =  height

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
        <Grid Background="{DynamicResource pyRevitAccentBrush}">
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
            <Style TargetType="{x:Type Button}">
                <Setter Property="FocusVisualStyle" Value="{x:Null}"/>
                    <Setter Property="Background" Value="#ffffff"/>
                    <Setter Property="BorderBrush" Value="#cccccc"/>
                    <Setter Property="BorderThickness" Value="0"/>
                    <Setter Property="Foreground" Value="{DynamicResource pyRevitDarkBrush}"/>
                    <Setter Property="HorizontalContentAlignment" Value="Center"/>
                    <Setter Property="VerticalContentAlignment" Value="Center"/>
                    <Setter Property="Padding" Value="8,2,8,2"/>
                    <Setter Property="Template">
                        <Setter.Value>
                            <ControlTemplate TargetType="{x:Type Button}">
                                <Border Background="{TemplateBinding Background}"
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
                                        <Setter Property="Foreground" Value="{DynamicResource pyRevitDarkBrush}" />
                                    </Trigger>
                                    <Trigger Property="IsMouseOver" Value="True">
                                        <Setter Property="Background" Value="#dddddd" />
                                        <Setter Property="BorderBrush" Value="#cccccc" />
                                        <Setter Property="Foreground" Value="{DynamicResource pyRevitDarkBrush}" />
                                    </Trigger>
                                    <Trigger Property="IsPressed" Value="True">
                                        <Setter Property="Background" Value="{DynamicResource pyRevitAccentBrush}" />
                                        <Setter Property="BorderBrush" Value="{DynamicResource pyRevitAccentBrush}"/>
                                        <Setter Property="Foreground" Value="#ffffff"/>
                                    </Trigger>
                                    <Trigger Property="IsFocused" Value="true">
                                        <Setter Property="BorderBrush" Value="{DynamicResource pyRevitAccentBrush}" />
                                    </Trigger>
                                </ControlTemplate.Triggers>
                            </ControlTemplate>
                        </Setter.Value>
                    </Setter>
            </Style>
            <Style TargetType="{x:Type ProgressBar}">
                <Setter Property="Background" Value="{DynamicResource pyRevitDarkBrush}" />
                <Setter Property="Foreground" Value="{DynamicResource pyRevitAccentBrush}" />
                <Setter Property="BorderBrush" Value="{x:Null}" />
                <Setter Property="BorderThickness" Value="0" />
                <Setter Property="IsTabStop" Value="False" />
                <Setter Property="Maximum" Value="100" />
                <Setter Property="Template">
                    <Setter.Value>
                        <ControlTemplate TargetType="ProgressBar">
                            <Grid x:Name="Root">
                                <Border x:Name="PART_Track"
                                        Background="{TemplateBinding Background}"
                                        BorderBrush="{TemplateBinding BorderBrush}"
                                        BorderThickness="{TemplateBinding BorderThickness}" />
                                <Grid x:Name="ProgressBarRootGrid">
                                    <Grid x:Name="IndeterminateRoot" Visibility="Collapsed">
                                        <Rectangle x:Name="IndeterminateSolidFill"
                                                   Margin="{TemplateBinding BorderThickness}"
                                                   Fill="{DynamicResource pyRevitAccentBrush}"
                                                   Opacity="1"
                                                   RenderTransformOrigin="0.5,0.5"
                                                   StrokeThickness="0" />
                                        <Rectangle x:Name="IndeterminateGradientFill"
                                                   Opacity=".2"
                                                   Margin="{TemplateBinding BorderThickness}"
                                                   StrokeThickness="1">
                                            <Rectangle.Fill>
                                                <LinearGradientBrush MappingMode="Absolute"
                                                                     SpreadMethod="Repeat"
                                                                     StartPoint="20,1" EndPoint="0,1">
                                                    <LinearGradientBrush.Transform>
                                                        <TransformGroup>
                                                            <TranslateTransform x:Name="xTransform" X="0" />
                                                            <SkewTransform AngleX="-30" />
                                                        </TransformGroup>
                                                    </LinearGradientBrush.Transform>
                                                    <GradientStop Offset="0"
                                                                  Color="{DynamicResource pyRevitAccentColor}" />
                                                    <GradientStop Offset="0.499"
                                                                  Color="{DynamicResource pyRevitAccentColor}" />
                                                    <GradientStop Offset="0.500" Color="White"/>
                                                    <GradientStop Offset="1.0" Color="White" />
                                                </LinearGradientBrush>
                                            </Rectangle.Fill>
                                        </Rectangle>
                                    </Grid>
                                    <Grid x:Name="DeterminateRoot">
                                        <Border x:Name="PART_Indicator"
                                                HorizontalAlignment="Left"
                                                Background="{DynamicResource pyRevitAccentBrush}">
                                            <Rectangle x:Name="GradientFill"
                                                   Opacity="0.7"
                                                   Visibility="Collapsed">
                                                <Rectangle.Fill>
                                                    <LinearGradientBrush MappingMode="Absolute"
                                                                         SpreadMethod="Repeat"
                                                                         StartPoint="20,1" EndPoint="0,1">
                                                        <LinearGradientBrush.Transform>
                                                            <TransformGroup>
                                                                <TranslateTransform X="0" />
                                                                <SkewTransform AngleX="-30" />
                                                            </TransformGroup>
                                                        </LinearGradientBrush.Transform>
                                                        <GradientStop Offset="0"
                                                                      Color="{DynamicResource pyRevitAccentColor}" />
                                                        <GradientStop Offset="0.651"
                                                                      Color="{DynamicResource pyRevitAccentColor}" />
                                                        <GradientStop Offset="0.093"
                                                                      Color="{DynamicResource pyRevitAccentColor}" />
                                                        <GradientStop Offset="0.548"
                                                                      Color="{DynamicResource pyRevitAccentColor}" />
                                                    </LinearGradientBrush>
                                                </Rectangle.Fill>
                                            </Rectangle>
                                        </Border>
                                    </Grid>
                                </Grid>
                                <VisualStateManager.VisualStateGroups>
                                    <VisualStateGroup x:Name="CommonStates">
                                        <VisualState x:Name="Determinate" />
                                        <VisualState x:Name="Indeterminate">
                                            <Storyboard RepeatBehavior="Forever">
                                                <ObjectAnimationUsingKeyFrames Storyboard.TargetName="IndeterminateRoot"
                                                                           Storyboard.TargetProperty="(UIElement.Visibility)"
                                                                           Duration="00:00:00">
                                                    <DiscreteObjectKeyFrame KeyTime="00:00:00">
                                                        <DiscreteObjectKeyFrame.Value>
                                                            <Visibility>Visible</Visibility>
                                                        </DiscreteObjectKeyFrame.Value>
                                                    </DiscreteObjectKeyFrame>
                                                </ObjectAnimationUsingKeyFrames>
                                                <ObjectAnimationUsingKeyFrames Storyboard.TargetName="DeterminateRoot"
                                                                           Storyboard.TargetProperty="(UIElement.Visibility)"
                                                                           Duration="00:00:00">
                                                    <DiscreteObjectKeyFrame KeyTime="00:00:00">
                                                        <DiscreteObjectKeyFrame.Value>
                                                            <Visibility>Collapsed</Visibility>
                                                        </DiscreteObjectKeyFrame.Value>
                                                    </DiscreteObjectKeyFrame>
                                                </ObjectAnimationUsingKeyFrames>
                                                <DoubleAnimationUsingKeyFrames Storyboard.TargetName="xTransform" Storyboard.TargetProperty="X">
                                                    <SplineDoubleKeyFrame KeyTime="0" Value="0" />
                                                    <SplineDoubleKeyFrame KeyTime="00:00:.35" Value="20" />
                                                </DoubleAnimationUsingKeyFrames>
                                            </Storyboard>
                                        </VisualState>
                                    </VisualStateGroup>
                                </VisualStateManager.VisualStateGroups>
                            </Grid>
                            <ControlTemplate.Triggers>
                                <Trigger Property="Orientation" Value="Vertical">
                                    <Setter TargetName="Root" Property="LayoutTransform">
                                        <Setter.Value>
                                            <RotateTransform Angle="-90" />
                                        </Setter.Value>
                                    </Setter>
                                </Trigger>
                                <Trigger Property="IsIndeterminate" Value="true">
                                    <Setter TargetName="DeterminateRoot" Property="Visibility" Value="Collapsed" />
                                    <Setter TargetName="IndeterminateRoot" Property="Visibility" Value="Visible" />
                                </Trigger>
                            </ControlTemplate.Triggers>
                        </ControlTemplate>
                    </Setter.Value>
                </Setter>
            </Style>
        </Window.Resources>
        <Grid Background="{DynamicResource pyRevitDarkBrush}">
            <ProgressBar x:Name="pbar"/>
            <TextBlock x:Name="pbar_text"
                       TextWrapping="Wrap" Text="TextBlock"
                       TextAlignment="Center" VerticalAlignment="Center"
                       Foreground="{DynamicResource {x:Static SystemColors.WindowBrushKey}}"/>
            <Button x:Name="cancel_b"
                    HorizontalAlignment="Left"
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
        self._title = kwargs.get('title', '{value}/{max_value}')

    def _update_pbar(self):
        self.update_window()
        self.pbar.Maximum = self.max_value
        self.pbar.Value = self.new_value

        # updating title
        title_text = \
            string.Formatter().vformat(self._title,
                                       (),
                                       coreutils.SafeDict(
                                           {'value': self.new_value,
                                            'max_value': self.max_value}
                                           ))

        self.pbar_text.Text = title_text

    @property
    def title(self):
        return self._title

    @title.setter
    def title(self, value):
        if type(value) == str:
            self._title = value

    @property
    def indeterminate(self):
        return self.pbar.IsIndeterminate

    @indeterminate.setter
    def indeterminate(self, value):
        self.pbar.IsIndeterminate = value

    def clicked_cancel(self, sender, args):
        self.cancel_b.Content = 'Cancelling...'
        self.cancelled = True

    def update_progress(self, new_value, max_value):
        self.max_value = max_value
        self.new_value = new_value
        self.pbar.Dispatcher.Invoke(System.Action(self._update_pbar),
                                    Threading.DispatcherPriority.Background)


class SearchPrompt(WPFWindow):
    def __init__(self, search_db, width, height, **kwargs):
        WPFWindow.__init__(self,
                           op.join(op.dirname(__file__), 'SearchPrompt.xaml'))
        self.Width = width
        self.MinWidth = self.Width
        self.Height = height

        self.search_tip = kwargs.get('search_tip', '')

        self._search_db = sorted(search_db)
        self.response = None

        self.search_tb.Focus()
        self.hide_element(self.tab_icon)
        self.hide_element(self.return_icon)
        self.search_tb.Text = ''
        self.set_search_results()

    @property
    def search_term(self):
        return self.search_tb.Text.lower().strip()

    @property
    def search_input(self):
        return self.search_tb.Text

    @property
    def search_matches(self):
        # remove duplicates while keeping order
        # results = list(set(self._search_results))
        return OrderedDict.fromkeys(self._search_results).keys()

    def update_search_term(self):
        self.search_tb.Text = self.response + ' '
        self.search_tb.CaretIndex = len(self.search_tb.Text)

    def update_results_display(self):
        self.directmatch_tb.Text = ''
        self.wordsmatch_tb.Text = ''

        results = self.search_matches
        res_cout = len(results)

        logger.debug('unique results count: {}'.format(res_cout))
        logger.debug('unique results: {}'.format(results))

        if res_cout > 1:
            self.show_element(self.tab_icon)
            self.hide_element(self.return_icon)
        elif res_cout == 1:
            self.hide_element(self.tab_icon)
            self.show_element(self.return_icon)
        else:
            self.hide_element(self.tab_icon)
            self.hide_element(self.return_icon)

        if self._result_index >= res_cout:
            self._result_index = 0

        if self._result_index < 0:
            self._result_index = res_cout - 1

        cur_txt = self.search_term

        if not cur_txt:
            self.directmatch_tb.Text = self.search_tip
            return

        if results:
            cur_res = results[self._result_index]
            logger.debug('current result: {}'.format(cur_res))
            if cur_res.lower().startswith(cur_txt):
                logger.debug('directmatch_tb.Text: {}'.format(cur_res))
                self.directmatch_tb.Text = \
                    self.search_tb.Text + cur_res[len(cur_txt):]
            else:
                logger.debug('wordsmatch_tb.Text: {}'.format(cur_res))
                self.wordsmatch_tb.Text = '- {}'.format(cur_res)

            self.response = cur_res
            return True

        self.response = None
        return False

    def set_search_results(self, *args):
        self._result_index = 0
        self._search_results = []

        for resultset in args:
            logger.debug('result set: {}'.format(resultset))
            self._search_results.extend(sorted(resultset))

        logger.debug('results: {}'.format(self._search_results))
        self.update_results_display()

    def find_direct_match(self):
        results = []
        cur_txt = self.search_term
        if cur_txt:
            for cmd_name in self._search_db:
                if cmd_name.lower().startswith(cur_txt):
                    results.append(cmd_name)

        return results

    def find_word_match(self):
        results = []
        cur_txt = self.search_term
        if cur_txt:
            cur_words = cur_txt.split(' ')
            for cmd_name in self._search_db:
                if all([x in cmd_name.lower() for x in cur_words]):
                    results.append(cmd_name)

        return results

    def search_txt_changed(self, sender, args):
        dmresults = self.find_direct_match()
        wordresults = self.find_word_match()
        logger.debug(len(dmresults), len(wordresults))
        self.set_search_results(dmresults, wordresults)

    def handle_kb_key(self, sender, args):
        if args.Key == framework.Windows.Input.Key.Escape:
            self.response = None
            self.Close()
        elif args.Key == framework.Windows.Input.Key.Enter:
            self.Close()
        elif args.Key == framework.Windows.Input.Key.Tab:
            if False:
                self.update_search_term()
            else:
                self._result_index += 1
                self.update_results_display()
        elif args.Key == framework.Windows.Input.Key.Down:
            self._result_index += 1
            self.update_results_display()
        elif args.Key == framework.Windows.Input.Key.Up:
            self._result_index -= 1
            self.update_results_display()

    @classmethod
    def show_prompt(cls, search_db,
                    width=600, height=100, **kwargs):
        dlg = cls(search_db, width, height, **kwargs)
        dlg.ShowDialog()
        return dlg.response


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
