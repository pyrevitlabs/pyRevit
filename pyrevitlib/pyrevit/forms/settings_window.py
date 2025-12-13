# -*- coding: utf-8 -*-
"""Dynamic Settings Window for pyRevit
Creates a reusable WPF window for managing script configurations.

Usage:
    from pyrevit import script
    from pyrevit.forms import settings_window

    settings = [
        {"name": "scope", "type": "choice", "label": "Scope",
         "options": ["Visibility", "Active State"], "default": "Visibility"},
        {"name": "set_workset", "type": "bool", "label": "Set Workset", "default": True},
        {"name": "tolerance", "type": "int", "label": "Tolerance (mm)",
         "default": 10, "min": 0, "max": 1000},
        {"name": "prefix", "type": "string", "label": "Prefix", "default": ""},
        {"name": "highlight_color", "type": "color", "label": "Highlight Color",
         "default": "#ffff0000"},
        {"name": "export_folder", "type": "folder", "label": "Export Folder", "default": ""},
        {"name": "template_file", "type": "file", "label": "Template File",
         "default": "", "file_ext": "rvt", "files_filter": "Revit Files (*.rvt)|*.rvt"},
    ]

    if settings_window.show_settings(settings, title="My Tool Settings"):
        print("Settings saved!")
"""

from pyrevit import script, forms


class SettingsWindow(forms.WPFWindow):
    """Dynamic settings window that generates UI from schema."""

    def __init__(
        self, settings_schema, section=None, title="Settings", width=450,
    ):
        """Initialize the settings window.

        Args:
            settings_schema: List of setting definitions
            section: Config section name
            title: Window title
            width: Window width in pixels
        """
        self.config = script.get_config(section)
        self.settings_schema = settings_schema
        self.window_title = title
        self.window_width = width
        self.config_section = section
        self.result = False
        self.controls = {}

        # Generate XAML
        xaml_string = self._generate_xaml()

        # Initialize WPF window with generated XAML
        forms.WPFWindow.__init__(self, xaml_string, literal_string=True)

        # Set window title
        self.Title = self.window_title

        # Populate controls with current values
        self._populate_values()

        # Wire up button events
        self.save_button.Click += self.save_clicked
        self.cancel_button.Click += self.cancel_clicked
        self.reset_button.Click += self.reset_clicked

    def _escape_xml(self, text):
        """Escape special XML characters.

        Args:
            text: Text to escape

        Returns:
            str: XML-escaped text
        """
        if not text:
            return ""
        return (
            str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
        )

    def _generate_xaml(self):
        """Generate XAML string based on settings schema."""

        # Start with window definition
        xaml_parts = [
            '<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"',
            '        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"',
            '        Title="Settings" Height="Auto" Width="{0}"'.format(
                self.window_width
            ),
            '        WindowStartupLocation="CenterScreen"',
            '        ResizeMode="CanResizeWithGrip"',
            '        ShowInTaskbar="False"',
            '        SizeToContent="Height">',
            "    <Window.Resources>",
            '        <Style TargetType="Label">',
            '            <Setter Property="Margin" Value="0,5,0,2"/>',
            '            <Setter Property="FontWeight" Value="SemiBold"/>',
            "        </Style>",
            '        <Style TargetType="TextBox">',
            '            <Setter Property="Margin" Value="0,0,0,4"/>',
            '            <Setter Property="Padding" Value="5,3"/>',
            "        </Style>",
            '        <Style TargetType="ComboBox">',
            '            <Setter Property="Margin" Value="0,0,0,4"/>',
            '            <Setter Property="Padding" Value="5,3"/>',
            "        </Style>",
            '        <Style TargetType="CheckBox">',
            '            <Setter Property="Margin" Value="0,5,0,4"/>',
            "        </Style>",
            '        <Style TargetType="Button" x:Key="BrowseButton">',
            '            <Setter Property="Margin" Value="5,0,0,4"/>',
            '            <Setter Property="Padding" Value="5,3"/>',
            '            <Setter Property="MinWidth" Value="30"/>',
            "        </Style>",
            "    </Window.Resources>",
            '    <Grid Margin="20">',
            "        <Grid.RowDefinitions>",
            '            <RowDefinition Height="Auto"/>',
            '            <RowDefinition Height="Auto"/>',
            "        </Grid.RowDefinitions>",
            "        ",
            "        <!-- Settings Stack Panel -->",
            '        <StackPanel Grid.Row="0" Margin="0,0,0,12">',
        ]

        # Generate controls for each setting
        for setting in self.settings_schema:
            setting_type = setting.get("type", "string")
            name = self._escape_xml(setting.get("name", ""))
            label = self._escape_xml(setting.get("label", setting.get("name", "")))

            if setting_type == "bool":
                xaml_parts.append(
                    '<CheckBox x:Name="{0}" Content="{1}"/>'.format(name, label)
                )

            elif setting_type == "choice":
                xaml_parts.append('<Label Content="{0}"/>'.format(label))
                xaml_parts.append('<ComboBox x:Name="{0}"/>'.format(name))

            elif setting_type in ["color", "folder", "file"]:
                xaml_parts.append('<Label Content="{0}"/>'.format(label))
                xaml_parts.append('<Grid Margin="0,0,0,4">')
                xaml_parts.append("<Grid.ColumnDefinitions>")
                xaml_parts.append('<ColumnDefinition Width="*"/>')
                xaml_parts.append('<ColumnDefinition Width="Auto"/>')
                xaml_parts.append("</Grid.ColumnDefinitions>")
                xaml_parts.append('<TextBox x:Name="{0}" Grid.Column="0"/>'.format(name))
                xaml_parts.append(
                    '<Button x:Name="{0}_button" Grid.Column="1" Content="..." '
                    'Style="{{StaticResource BrowseButton}}"/>'.format(name)
                )
                xaml_parts.append("</Grid>")

            elif setting_type in ["int", "float", "string"]:
                xaml_parts.append('<Label Content="{0}"/>'.format(label))
                xaml_parts.append('<TextBox x:Name="{0}"/>'.format(name))

        # Add buttons
        xaml_parts.extend(
            [
                "        </StackPanel>",
                '        <StackPanel Grid.Row="1" Orientation="Horizontal" HorizontalAlignment="Right">',
                '            <Button x:Name="reset_button" Content="Reset" Width="80" Height="30" '
                '                       Margin="0,0,10,0"/>',
                '            <Button x:Name="save_button" Content="Save" Width="80" Height="30" '
                '                       Margin="0,0,10,0" IsDefault="True"/>',
                '            <Button x:Name="cancel_button" Content="Cancel" Width="80" Height="30" IsCancel="True"/>',
                "        </StackPanel>",
                "    </Grid>",
                "</Window>",
            ]
        )

        return "\n".join(xaml_parts)

    def _populate_values(self):
        """Populate controls with current config values."""
        for setting in self.settings_schema:
            name = setting.get("name")
            setting_type = setting.get("type", "string")
            default = setting.get("default")

            # Get current value from config or use default
            current_value = self.config.get_option(name, default)

            # Get the control
            control = getattr(self, name, None)
            if not control:
                continue

            self.controls[name] = control

            # Set value based on type
            if setting_type == "bool":
                control.IsChecked = bool(current_value)

            elif setting_type == "choice":
                options = setting.get("options", [])
                control.ItemsSource = options
                if current_value in options:
                    control.SelectedItem = current_value
                elif options:
                    control.SelectedIndex = 0

            elif setting_type in ["int", "float", "string", "color", "folder", "file"]:
                control.Text = str(current_value) if current_value is not None else ""

                # Wire up browse buttons for color, folder, and file types
                if setting_type in ["color", "folder", "file"]:
                    button = getattr(self, name + "_button", None)
                    if button:
                        if setting_type == "color":
                            button.Click += lambda s, e, n=name: self._pick_color(n)
                        elif setting_type == "folder":
                            button.Click += lambda s, e, n=name: self._pick_folder(n)
                        elif setting_type == "file":
                            button.Click += (
                                lambda s, e, n=name, st=setting: self._pick_file(n, st)
                            )

    def _pick_color(self, control_name):
        """Show color picker and update control.

        Args:
            control_name: Name of the control to update
        """
        control = self.controls.get(control_name)
        if not control:
            return

        current_value = control.Text if control.Text else None
        selected_color = forms.ask_for_color(default=current_value)

        if selected_color:
            control.Text = selected_color

    def _pick_folder(self, control_name):
        """Show folder picker and update control.

        Args:
            control_name: Name of the control to update
        """
        control = self.controls.get(control_name)
        if not control:
            return

        selected_folder = forms.pick_folder()

        if selected_folder:
            control.Text = selected_folder

    def _pick_file(self, control_name, setting):
        """Show file picker and update control.

        Args:
            control_name: Name of the control to update
            setting: Setting definition dict
        """
        control = self.controls.get(control_name)
        if not control:
            return

        file_ext = setting.get("file_ext", "*")
        files_filter = setting.get("files_filter", "")
        init_dir = setting.get("init_dir", "")
        multi_file = setting.get("multi_file", False)

        selected_file = forms.pick_file(
            file_ext=file_ext,
            files_filter=files_filter,
            init_dir=init_dir,
            multi_file=multi_file,
        )

        if selected_file:
            control.Text = selected_file

    def _validate_numeric(self, setting, value, conversion_func, type_name):
        """Validate numeric setting values.

        Args:
            setting: Setting definition dict
            value: Value to validate
            conversion_func: Function to convert string to number (int or float)
            type_name: Type name for error messages

        Returns:
            tuple: (is_valid, validated_value, error_message)
        """
        name = setting.get("name")
        label = setting.get("label", name)

        try:
            val = conversion_func(value)
            min_val = conversion_func(setting.get("min"))
            max_val = conversion_func(setting.get("max"))

            if min_val is not None and val < min_val:
                return (
                    False,
                    None,
                    "{0} must be at least {1}".format(label, min_val),
                )
            if max_val is not None and val > max_val:
                return False, None, "{0} must be at most {1}".format(label, max_val)

            return True, val, None

        except ValueError:
            return False, None, "{0} must be a valid {1}".format(label, type_name)

    def _validate_setting(self, setting, value):
        """Validate a setting value.

        Args:
            setting: Setting definition dict
            value: Value to validate

        Returns:
            tuple: (is_valid, validated_value, error_message)
        """
        setting_type = setting.get("type", "string")
        name = setting.get("name")
        label = setting.get("label", name)

        if setting_type == "int":
            return self._validate_numeric(setting, value, int, "number")

        elif setting_type == "float":
            return self._validate_numeric(setting, value, float, "number")

        elif setting_type in ["string", "color", "folder", "file"]:
            # Check for required field
            if setting.get("required", False) and not value.strip():
                return False, None, "{0} is required".format(label)
            return True, value, None

        elif setting_type == "bool":
            return True, bool(value), None

        elif setting_type == "choice":
            options = setting.get("options", [])
            if value not in options:
                return (
                    False,
                    None,
                    "{0} must be one of: {1}".format(label, ", ".join(options)),
                )
            return True, value, None

        return True, value, None

    def save_clicked(self, sender, args):
        """Handle save button click."""
        errors = []
        validated_values = {}

        # Validate all values first
        for setting in self.settings_schema:
            name = setting.get("name")
            setting_type = setting.get("type", "string")
            control = self.controls.get(name)

            if not control:
                continue

            # Get value from control
            if setting_type == "bool":
                value = control.IsChecked
            elif setting_type == "choice":
                value = control.SelectedItem
            else:
                value = control.Text

            # Validate
            is_valid, validated_value, error_msg = self._validate_setting(
                setting, value
            )

            if not is_valid:
                errors.append(error_msg)
            else:
                validated_values[name] = validated_value

        # Show errors if any
        if errors:
            forms.alert("\n".join(errors), title="Validation Error", warn_icon=True)
            return

        # Only save if all validations passed
        for setting in self.settings_schema:
            name = setting.get("name")
            if name in validated_values:
                self.config.set_option(name, validated_values[name])

        # Save config
        script.save_config()

        self.result = True
        self.Close()

    def cancel_clicked(self, sender, args):
        """Handle cancel button click."""
        self.result = False
        self.Close()

    def reset_clicked(self, sender, args):
        """Handle reset button click."""
        # Confirm with user
        if forms.alert(
            "Are you sure you want to reset all settings, removing it from the .ini?",
            title="Reset Settings",
            yes=True,
            no=True,
        ):
            script.reset_config(self.config_section)
            self.result = False
            self.Close()


def show_settings(settings_schema, section=None, title="Settings", width=450):
    """Show settings window and return True if saved.

    Args:
        config: pyRevit config object from script.get_config()
        settings_schema: List of setting definitions. Each setting is a dict with:
            - name (str): Setting key name for config
            - type (str): "bool", "choice", "int", "float", "string", "color", "folder", or "file"
            - label (str): Display label for the setting
            - default: Default value if not in config
            - options (list): For "choice" type, list of options
            - min (int/float): For "int"/"float" type, minimum value
            - max (int/float): For "int"/"float" type, maximum value
            - required (bool): For "string" type, whether field is required
            - file_ext (str): For "file" type, file extension filter (e.g., "rvt")
            - files_filter (str): For "file" type, files filter (e.g., "Revit Files (*.rvt)|*.rvt")
            - init_dir (str): For "file" type, initial directory
            - multi_file (bool): For "file" type, allow multiple file selection
        title (str): Window title
        width (int): Window width in pixels (default: 450)
        section (str): Config section name for reset functionality

    Returns:
        bool: True if settings were saved, False if canceled

    Example:
        ```python
        settings = [
            {"name": "scope", "type": "choice", "label": "Scope",
             "options": ["Visibility", "Active State"], "default": "Visibility"},
            {"name": "set_workset", "type": "bool", "label": "Set Workset", "default": True},
            {"name": "tolerance", "type": "int", "label": "Tolerance (mm)",
             "default": 10, "min": 0, "max": 1000},
            {"name": "highlight_color", "type": "color", "label": "Highlight Color",
             "default": "#ffff0000"},
            {"name": "export_folder", "type": "folder", "label": "Export Folder", "default": ""},
            {"name": "template_file", "type": "file", "label": "Template File",
             "default": "", "file_ext": "rvt", "files_filter": "Revit Files (*.rvt)|*.rvt"},
        ]

        if show_settings(config, settings, title="My Tool Settings", section="MyToolSection"):
            print("Settings saved!")
        ```
    """
    window = SettingsWindow(settings_schema, section, title, width)
    window.ShowDialog()
    return window.result
