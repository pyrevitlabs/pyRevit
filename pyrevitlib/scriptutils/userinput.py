import clr

from scriptutils.forms import WPFWindow

clr.AddReferenceByPartialName('System.Windows.Forms')

# noinspection PyUnresolvedReferences
from System.Windows.Forms import FolderBrowserDialog, DialogResult, OpenFileDialog


class TemplateUserInputWindow(WPFWindow):
    layout = """
    <Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
            xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
            ShowInTaskbar="False" ResizeMode="NoResize"
            WindowStartupLocation="CenterScreen" HorizontalContentAlignment="Center">
    </Window>
    """

    def __init__(self, context, title, width, height, **kwargs):
        WPFWindow.__init__(self, self.layout, literal_string=True)
        self.Title = title
        self.Width = width
        self.Height = height

        self._context = context
        self.response = None

        self._setup(**kwargs)

    def _setup(self, **kwargs):
        pass

    @classmethod
    def show(cls, context, title='User Input', width=300, height=400, **kwargs):
        dlg = cls(context, title, width, height, **kwargs)
        dlg.ShowDialog()
        return dlg.response


class SelectFromList(TemplateUserInputWindow):
    layout = """
    <Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
            xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
            ShowInTaskbar="False" ResizeMode="NoResize"
            WindowStartupLocation="CenterScreen" HorizontalContentAlignment="Center">
            <Window.Resources>
                <Style x:Key="ClearButton" TargetType="Button">
                    <Setter Property="Background" Value="White"/>
                </Style>
            </Window.Resources>
            <DockPanel Margin="10">
                <DockPanel DockPanel.Dock="Top" Margin="0,0,0,10">
                    <TextBlock FontSize="14" Margin="0,3,10,0" DockPanel.Dock="Left">Filter:</TextBlock>
                    <StackPanel>
                        <TextBox x:Name="search_tb" Height="25px" TextChanged="search_txt_changed"/>
                        <Button Style="{StaticResource ClearButton}" HorizontalAlignment="Right"
                                x:Name="clrsearch_b" Content="x" Margin="0,-25,5,0" Padding="0,-4,0,0"
                                Click="clear_search" Width="15px" Height="15px"/>
                    </StackPanel>
                </DockPanel>
                <Button Content="Select" Click="button_select" DockPanel.Dock="Bottom" Margin="0,10,0,0"/>
                <ListView x:Name="list_lb" />
            </DockPanel>
    </Window>
    """

    def _setup(self, **kwargs):
        self.hide_element(self.clrsearch_b)
        self.clear_search(None, None)
        self.search_tb.Focus()

        if 'multiselect' in kwargs and not kwargs['multiselect']:
            self.list_lb.SelectionMode = SelectionMode.Single
        else:
            self.list_lb.SelectionMode = SelectionMode.Extended

        self._list_options()

    def _list_options(self, option_filter=None):
        if option_filter:
            option_filter = option_filter.lower()
            self.list_lb.ItemsSource = [str(option) for option in self._context
                                        if option_filter in str(option).lower()]
        else:
            self.list_lb.ItemsSource = [str(option) for option in self._context]

    def _get_options(self):
        return [option for option in self._context if str(option) in self.list_lb.SelectedItems]

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def button_select(self, sender, args):
        self.response = self._get_options()
        self.Close()

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def search_txt_changed(self, sender, args):
        if self.search_tb.Text == '':
            self.hide_element(self.clrsearch_b)
        else:
            self.show_element(self.clrsearch_b)

        self._list_options(option_filter=self.search_tb.Text)

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def clear_search(self, sender, args):
        self.search_tb.Text = ' '
        self.search_tb.Clear()
        self.list_lb.ItemsSource = self._context


class SelectFromCheckBoxes(TemplateUserInputWindow):
    layout = """
    <Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
            xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
            ShowInTaskbar="False" ResizeMode="NoResize"
            WindowStartupLocation="CenterScreen" HorizontalContentAlignment="Center">
            <Window.Resources>
                <Style x:Key="ClearButton" TargetType="Button">
                    <Setter Property="Background" Value="White"/>
                </Style>
            </Window.Resources>
            <DockPanel Margin="10">
                <DockPanel DockPanel.Dock="Top" Margin="0,0,0,10">
                    <TextBlock FontSize="14" Margin="0,3,10,0" DockPanel.Dock="Left">Filter:</TextBlock>
                    <StackPanel>
                        <TextBox x:Name="search_tb" Height="25px" TextChanged="search_txt_changed"/>
                        <Button Style="{StaticResource ClearButton}" HorizontalAlignment="Right"
                                x:Name="clrsearch_b" Content="x" Margin="0,-25,5,0" Padding="0,-4,0,0"
                                Click="clear_search" Width="15px" Height="15px"/>
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
                        <Button x:Name="checkall_b" Grid.Column="0" Grid.Row="0"
                                Content="Check" Click="check_all" Margin="0,10,3,0"/>
                        <Button x:Name="uncheckall_b" Grid.Column="1" Grid.Row="0"
                                Content="Uncheck" Click="uncheck_all" Margin="3,10,3,0"/>
                        <Button x:Name="toggleall_b" Grid.Column="2" Grid.Row="0"
                                Content="Toggle" Click="toggle_all" Margin="3,10,0,0"/>
                    </Grid>
                    <Button x:Name="select_b" Content="" Click="button_select" Margin="0,10,0,0"/>
                </StackPanel>
                <ListView x:Name="list_lb">
                    <ListView.ItemTemplate>
                         <DataTemplate>
                           <StackPanel>
                             <CheckBox Content="{Binding name}" IsChecked="{Binding state}"/>
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
        # if 'button_color' in kwargs:
        #     color_tuple = kwargs['button_color']
        #     color_brush = SolidColorBrush(Color.FromRgb(color_tuple[0], color_tuple[1], color_tuple[2]));
        #     self.select_b.Background = color_brush

        self._list_options()

    def _list_options(self, checkbox_filter=None):
        if checkbox_filter:
            self.checkall_b.Content = 'Check'
            self.uncheckall_b.Content = 'Uncheck'
            self.toggleall_b.Content = 'Toggle'
            checkbox_filter = checkbox_filter.lower()
            self.list_lb.ItemsSource = [checkbox for checkbox in self._context
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

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def toggle_all(self, sender, args):
        self._set_states(flip=True)

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def check_all(self, sender, args):
        self._set_states(state=True)

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def uncheck_all(self, sender, args):
        self._set_states(state=False)

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def button_select(self, sender, args):
        self.response = self._context
        self.Close()

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def search_txt_changed(self, sender, args):
        if self.search_tb.Text == '':
            self.hide_element(self.clrsearch_b)
        else:
            self.show_element(self.clrsearch_b)

        self._list_options(checkbox_filter=self.search_tb.Text)

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def clear_search(self, sender, args):
        self.search_tb.Text = ' '
        self.search_tb.Clear()
        self.list_lb.ItemsSource = self._context


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
