from pyrevit.loader import sessionmgr
from pyrevit import forms
from pyrevit import framework
from pyrevit import script


logger = script.get_logger()


class ConsolePrompt(forms.TemplateUserInputWindow):
    layout = """
    <Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
                xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
                ShowInTaskbar="False" ResizeMode="NoResize"
                WindowStartupLocation="CenterScreen"
                HorizontalContentAlignment="Center"
                WindowStyle="None"
                AllowsTransparency="True"
                Background="#00FFFFFF"
                SizeToContent="WidthAndHeight"
                PreviewKeyDown="handle_kb_key">
        <Window.Resources>
            <Canvas x:Key="SearchIcon">
                <Path Data="M9.5,3A6.5,6.5 0 0,1 16,9.5C16,11.11 15.41,12.59 14.44,13.73L14.71,14H15.5L20.5,19L19,20.5L14,15.5V14.71L13.73,14.44C12.59,15.41 11.11,16 9.5,16A6.5,6.5 0 0,1 3,9.5A6.5,6.5 0 0,1 9.5,3M9.5,5C7,5 5,7 5,9.5C5,12 7,14 9.5,14C12,14 14,12 14,9.5C14,7 12,5 9.5,5Z"
                      Fill="White"/>
                <Canvas.LayoutTransform>
                    <ScaleTransform ScaleX="1.8" ScaleY="1.8"/>
                </Canvas.LayoutTransform>
            </Canvas>
            <Canvas x:Key="TabIcon">
                <Path Data="M20,18H22V6H20M11.59,7.41L15.17,11H1V13H15.17L11.59,16.58L13,18L19,12L13,6L11.59,7.41Z"
                      Fill="LightGray" />
                <Canvas.LayoutTransform>
                    <ScaleTransform ScaleX="1.5" ScaleY="1.5"/>
                </Canvas.LayoutTransform>
            </Canvas>
            <Style TargetType="{x:Type TextBox}">
                <Setter Property="SnapsToDevicePixels" Value="True"/>
                <Setter Property="OverridesDefaultStyle" Value="True"/>
                <Setter Property="FocusVisualStyle" Value="{x:Null}"/>
                <Setter Property="AllowDrop" Value="False"/>
                <Setter Property="FontSize" Value="26"/>
                <Setter Property="Foreground" Value="White"/>
                <Setter Property="CaretBrush" Value="#00000000"/>
                <Setter Property="Template">
                    <Setter.Value>
                        <ControlTemplate TargetType="{x:Type TextBoxBase}">
                            <Border Name="Border"
                                    Padding="2"
                                    Background="{x:Null}"
                                    BorderBrush="{x:Null}"
                                    BorderThickness="0" >
                                <ScrollViewer Margin="0" x:Name="PART_ContentHost"/>
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
        </Window.Resources>
        <Border CornerRadius="15" Height="64" Background="#f323303d">
            <DockPanel Margin="10,10,10,10">
                <ContentControl DockPanel.Dock="Left"
                                Height="44" Width="44"
                                Content="{StaticResource SearchIcon}"
                                KeyboardNavigation.IsTabStop="False"/>
                <ContentControl x:Name="tab_icon"
                                DockPanel.Dock="Right"
                                Visibility="Collapsed"
                                Margin="5,0,5,0"
                                Height="36" Width="36"
                                Content="{StaticResource TabIcon}"
                                KeyboardNavigation.IsTabStop="False"/>
                <Grid>
                    <TextBox x:Name="directmatch_tb"
                             IsEnabled="False"
                             Foreground="LightGray"
                             Margin="10,0,0,0"
                             KeyboardNavigation.IsTabStop="False"/>
                    <StackPanel Orientation="Horizontal">
                        <TextBox x:Name="search_tb"
                                 Margin="10,0,0,0"
                                 TextChanged="search_txt_changed"/>
                        <TextBox x:Name="wordsmatch_tb"
                                 IsEnabled="False"
                                 Foreground="LightGray"
                                 KeyboardNavigation.IsTabStop="False"/>
                    </StackPanel>
                </Grid>
            </DockPanel>
        </Border>
    </Window>
    """

    def _setup(self, **kwargs):
        self.search_tb.Focus()
        self.MinWidth = self.Width
        self._context = sorted(self._context)
        self.set_search_results()

    def update_results_display(self):
        self.directmatch_tb.Text = ''
        self.wordsmatch_tb.Text = ''

        results = sorted(set(self._search_results))
        res_cout = len(results)

        logger.debug(res_cout)
        logger.debug(results)

        if res_cout > 1:
            self.show_element(self.tab_icon)
        else:
            self.hide_element(self.tab_icon)

        if self._result_index >= res_cout:
            self._result_index = 0

        cur_txt = self.search_tb.Text.lower()

        if not cur_txt:
            self.directmatch_tb.Text = 'pyRevit Search'
            return

        if results:
            cur_res = results[self._result_index]
            logger.debug(cur_res)
            if cur_res.lower().startswith(cur_txt):
                logger.debug('directmatch_tb.Text', cur_res)
                self.directmatch_tb.Text = \
                    self.search_tb.Text + cur_res[len(cur_txt):]
            else:
                logger.debug('wordsmatch_tb.Text', cur_res)
                self.wordsmatch_tb.Text = '- {}'.format(cur_res)

            self.response = cur_res
            return True

        self.response = None
        return False

    def set_search_results(self, *args):
        self._result_index = 0
        self._search_results = []

        for resultset in args:
            self._search_results.extend(resultset)

        self.update_results_display()

    def find_direct_match(self):
        results = []
        cur_txt = self.search_tb.Text.lower()
        if cur_txt:
            for cmd_name in self._context:
                if cmd_name.lower().startswith(cur_txt):
                    results.append(cmd_name)

        return results

    def find_word_match(self):
        results = []
        cur_txt = self.search_tb.Text.lower()
        if cur_txt:
            cur_words = cur_txt.split(' ')
            for cmd_name in self._context:
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
            self._result_index += 1
            self.update_results_display()


pyrevit_cmds = {}


# find all available commands (for current selection)
# in currently active document
for cmd in sessionmgr.find_all_available_commands():
    cmd_inst = cmd()
    if hasattr(cmd_inst, 'baked_cmdName'):
        pyrevit_cmds[cmd_inst.baked_cmdName] = cmd


selected_cmd_name = ConsolePrompt.show(pyrevit_cmds.keys(),
                                       width=600, height=100)

if selected_cmd_name:
    selected_cmd = pyrevit_cmds[selected_cmd_name]
    sessionmgr.execute_command_cls(selected_cmd)
