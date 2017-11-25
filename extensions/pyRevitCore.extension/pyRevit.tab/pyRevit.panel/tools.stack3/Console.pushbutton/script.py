from pyrevit.loader import sessionmgr
from pyrevit import forms
from pyrevit import framework


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
                SizeToContent="Height"
                PreviewKeyDown="handle_esc_key">
        <Window.Resources>
            <Canvas x:Key="SearchIcon">
                <Path Data="M9.5,3A6.5,6.5 0 0,1 16,9.5C16,11.11 15.41,12.59 14.44,13.73L14.71,14H15.5L20.5,19L19,20.5L14,15.5V14.71L13.73,14.44C12.59,15.41 11.11,16 9.5,16A6.5,6.5 0 0,1 3,9.5A6.5,6.5 0 0,1 9.5,3M9.5,5C7,5 5,7 5,9.5C5,12 7,14 9.5,14C12,14 14,12 14,9.5C14,7 12,5 9.5,5Z"
                      Fill="White"/>
                <Canvas.LayoutTransform>
                    <ScaleTransform ScaleX="1.8" ScaleY="1.8"/>
                </Canvas.LayoutTransform>
            </Canvas>
            <Style TargetType="{x:Type TextBox}">
                <Setter Property="SnapsToDevicePixels" Value="True"/>
                <Setter Property="OverridesDefaultStyle" Value="True"/>
                <Setter Property="FocusVisualStyle" Value="{x:Null}"/>
                <Setter Property="AllowDrop" Value="False"/>
                <Setter Property="FontSize" Value="26"/>
                <Setter Property="Foreground" Value="White"/>
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
                                Content="{StaticResource SearchIcon}">
                </ContentControl>
                <Grid>
                    <TextBox x:Name="search_results_tb"
                             IsEnabled="False"
                             Foreground="LightGray"
                             Margin="10,0,0,0"/>
                    <TextBox x:Name="search_tb"
                             Margin="10,0,0,0"
                             TextChanged="search_txt_changed"/>
                </Grid>
            </DockPanel>
        </Border>
    </Window>
    """

    def _setup(self, **kwargs):
        self.search_tb.Focus()
        pass

    def search_txt_changed(self, sender, args):
        matchlist = [x for x in self._context
                     if self.search_tb.Text.lower() in x.lower()]
        if len(matchlist) == 1:
            self.search_tb.Text = matchlist[0]

    def handle_esc_key(self, sender, args):
        if args.Key == framework.Windows.Input.Key.Escape:
            self.Close()
        elif args.Key == framework.Windows.Input.Key.Enter:
            self.response = self.search_tb.Text
            self.Close()


pyrevit_cmds = {}


for cmd in sessionmgr.find_all_available_commands():
    cmd_inst = cmd()
    if hasattr(cmd_inst, 'baked_cmdName'):
        pyrevit_cmds[cmd_inst.baked_cmdName] = cmd


selected_cmd_name = ConsolePrompt.show(pyrevit_cmds.keys(),
                                       width=600, height=100)

if selected_cmd_name:
    selected_cmd = pyrevit_cmds[selected_cmd_name]
    sessionmgr.execute_command_cls(selected_cmd)
