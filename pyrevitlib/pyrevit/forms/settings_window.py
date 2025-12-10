# -*- coding: utf-8 -*-
"""Dynamic Settings Window for pyRevit
Creates a reusable WPF window for managing script configurations.

Usage:
    from pyrevit import script
    from pyrevit.forms import settings_window

    my_config = script.get_config()

    settings = [
        {"name": "scope", "type": "choice", "label": "Scope",
         "options": ["Visibility", "Active State"], "default": "Visibility"},
        {"name": "set_workset", "type": "bool", "label": "Set Workset", "default": True},
        {"name": "tolerance", "type": "int", "label": "Tolerance (mm)",
         "default": 10, "min": 0, "max": 1000},
        {"name": "prefix", "type": "string", "label": "Prefix", "default": ""},
    ]

    if settings_window.show_settings(my_config, settings, title="My Tool Settings"):
        print("Settings saved!")
"""

from pyrevit import script, forms


class SettingsWindow(forms.WPFWindow):
    """Dynamic settings window that generates UI from schema."""

    def __init__(self, config, settings_schema, title="Settings"):
        """Initialize the settings window.

        Args:
            config: pyRevit config object from script.get_config()
            settings_schema: List of setting definitions
            title: Window title
        """
        self.config = config
        self.settings_schema = settings_schema
        self.window_title = title
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

    def _generate_xaml(self):
        """Generate XAML string based on settings schema."""

        # Start with window definition
        xaml_parts = [
            '<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"',
            '        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"',
            '        Title="Settings" Height="Auto" Width="450"',
            '        WindowStartupLocation="CenterScreen"',
            '        ResizeMode="NoResize"',
            '        ShowInTaskbar="False"',
            '        SizeToContent="Height">',
            "    <Window.Resources>",
            '        <Style TargetType="Label">',
            '            <Setter Property="Margin" Value="0,5,0,2"/>',
            '            <Setter Property="FontWeight" Value="SemiBold"/>',
            "        </Style>",
            '        <Style TargetType="TextBox">',
            '            <Setter Property="Margin" Value="0,0,0,10"/>',
            '            <Setter Property="Padding" Value="5,3"/>',
            "        </Style>",
            '        <Style TargetType="ComboBox">',
            '            <Setter Property="Margin" Value="0,0,0,10"/>',
            '            <Setter Property="Padding" Value="5,3"/>',
            "        </Style>",
            '        <Style TargetType="CheckBox">',
            '            <Setter Property="Margin" Value="0,5,0,10"/>',
            "        </Style>",
            "    </Window.Resources>",
            '    <Grid Margin="20">',
            "        <Grid.RowDefinitions>",
            '            <RowDefinition Height="Auto"/>',
            '            <RowDefinition Height="Auto"/>',
            "        </Grid.RowDefinitions>",
            "        ",
            "        <!-- Settings Stack Panel -->",
            '        <StackPanel Grid.Row="0" Margin="0,0,0,20">',
        ]

        # Generate controls for each setting
        for setting in self.settings_schema:
            setting_type = setting.get("type", "string")
            name = setting.get("name", "")
            label = setting.get("label", name)

            if setting_type == "bool":
                xaml_parts.append(
                    '            <CheckBox x:Name="{0}" Content="{1}"/>'.format(
                        name, label
                    )
                )

            elif setting_type == "choice":
                xaml_parts.append('            <Label Content="{0}"/>'.format(label))
                xaml_parts.append('            <ComboBox x:Name="{0}"/>'.format(name))

            elif setting_type in ["int", "float", "string"]:
                xaml_parts.append('            <Label Content="{0}"/>'.format(label))
                xaml_parts.append('            <TextBox x:Name="{0}"/>'.format(name))

        # Add buttons
        xaml_parts.extend(
            [
                "        </StackPanel>",
                "        ",
                "        <!-- Buttons -->",
                '        <StackPanel Grid.Row="1" Orientation="Horizontal" HorizontalAlignment="Right">',
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

            elif setting_type in ["int", "float", "string"]:
                control.Text = str(current_value) if current_value is not None else ""

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

        try:
            if setting_type == "int":
                val = int(value)
                min_val = setting.get("min")
                max_val = setting.get("max")

                if min_val is not None and val < min_val:
                    return (
                        False,
                        None,
                        "{0} must be at least {1}".format(label, min_val),
                    )
                if max_val is not None and val > max_val:
                    return False, None, "{0} must be at most {1}".format(label, max_val)

                return True, val, None

            elif setting_type == "float":
                val = float(value)
                min_val = setting.get("min")
                max_val = setting.get("max")

                if min_val is not None and val < min_val:
                    return (
                        False,
                        None,
                        "{0} must be at least {1}".format(label, min_val),
                    )
                if max_val is not None and val > max_val:
                    return False, None, "{0} must be at most {1}".format(label, max_val)

                return True, val, None

            elif setting_type == "string":
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

        except ValueError:
            type_name = "number" if setting_type in ["int", "float"] else setting_type
            return False, None, "{0} must be a valid {1}".format(label, type_name)

    def save_clicked(self, sender, args):
        """Handle save button click."""
        errors = []

        # Validate and collect all values
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
                # Save to config
                self.config.set_option(name, validated_value)

        # Show errors if any
        if errors:
            forms.alert("\n".join(errors), title="Validation Error", warn_icon=True)
            return

        # Save config
        script.save_config()

        self.result = True
        self.Close()

    def cancel_clicked(self, sender, args):
        """Handle cancel button click."""
        self.result = False
        self.Close()


def show_settings(config, settings_schema, title="Settings"):
    """Show settings window and return True if saved.

    Args:
        config: pyRevit config object from script.get_config()
        settings_schema: List of setting definitions. Each setting is a dict with:
            - name (str): Setting key name for config
            - type (str): "bool", "choice", "int", "float", or "string"
            - label (str): Display label for the setting
            - default: Default value if not in config
            - options (list): For "choice" type, list of options
            - min (int/float): For "int"/"float" type, minimum value
            - max (int/float): For "int"/"float" type, maximum value
            - required (bool): For "string" type, whether field is required
        title (str): Window title

    Returns:
        bool: True if settings were saved, False if canceled

    Example:
        settings = [
            {"name": "scope", "type": "choice", "label": "Scope",
             "options": ["Visibility", "Active State"], "default": "Visibility"},
            {"name": "set_workset", "type": "bool", "label": "Set Workset", "default": True},
            {"name": "tolerance", "type": "int", "label": "Tolerance (mm)",
             "default": 10, "min": 0, "max": 1000},
        ]

        config = script.get_config()
        if show_settings(config, settings, title="My Tool Settings"):
            print("Settings saved!")
    """
    window = SettingsWindow(config, settings_schema, title)
    window.ShowDialog()
    return window.result
