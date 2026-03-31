# -*- coding: utf-8 -*-
"""Dynamic Settings Window for pyRevit
Creates a reusable WPF window for managing script configurations.

Usage:
    from pyrevit import script
    from pyrevit.forms import settings_window

    settings = [
        {"type": "section", "label": "Display"},
        {"name": "scope", "type": "choice", "label": "Scope",
         "options": ["Visibility", "Active State"], "default": "Visibility"},
        {"name": "highlight_color", "type": "color", "label": "Highlight Color",
         "default": "#ffff0000"},

        {"type": "section", "label": "Processing"},
        {"name": "set_workset", "type": "bool", "label": "Set Workset", "default": True},
        {"name": "tolerance", "type": "slider", "label": "Tolerance (mm)",
         "default": 10, "min": 0, "max": 1000},
        {"name": "prefix", "type": "string", "label": "Prefix", "default": ""},

        {"type": "section", "label": "Paths"},
        {"name": "export_folder", "type": "folder", "label": "Export Folder", "default": ""},
        {"name": "template_file", "type": "file", "label": "Template File",
         "default": "", "file_ext": "rvt", "files_filter": "Revit Files (*.rvt)|*.rvt"},
    ]

    if settings_window.show_settings(settings, title="My Tool Settings"):
        print("Settings saved!")
"""

from pyrevit import script, forms
from pyrevit.framework import Color, SolidColorBrush

# Setting types that are purely visual and carry no config value.
_DISPLAY_ONLY_TYPES = ("section", "separator")


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

        xaml_string = self._generate_xaml()
        forms.WPFWindow.__init__(self, xaml_string, literal_string=True)

        self.Title = self.window_title
        self._populate_values()

        self.save_button.Click += self.save_clicked
        self.cancel_button.Click += self.cancel_clicked
        self.reset_button.Click += self.reset_clicked

    # ------------------------------------------------------------------
    # XAML helpers
    # ------------------------------------------------------------------

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
            '        <Style TargetType="Slider">',
            '            <Setter Property="Margin" Value="0,4,0,4"/>',
            '            <Setter Property="VerticalAlignment" Value="Center"/>',
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

        for setting in self.settings_schema:
            setting_type = setting.get("type", "string")
            name = self._escape_xml(setting.get("name", ""))
            label = self._escape_xml(setting.get("label", setting.get("name", "")))

            # ---- Display-only / structural types --------------------------------

            if setting_type == "section":
                # Bold heading text + a full-width separator line beneath it.
                # First section gets less top margin to avoid excessive whitespace
                # at the very top of the panel.
                xaml_parts.append(
                    '<TextBlock Text="{0}"'
                    ' FontWeight="Bold" FontSize="12"'
                    ' Foreground="#555555"'
                    ' Margin="0,14,0,3"/>'.format(label)
                )
                xaml_parts.append('<Separator Margin="0,0,0,8" Background="#CCCCCC"/>')

            elif setting_type == "separator":
                # Bare horizontal rule, no label.
                xaml_parts.append('<Separator Margin="0,10,0,10" Background="#DDDDDD"/>')

            # ---- Interactive types ----------------------------------------------

            elif setting_type == "bool":
                xaml_parts.append(
                    '<CheckBox x:Name="{0}" Content="{1}"/>'.format(name, label)
                )

            elif setting_type == "choice":
                xaml_parts.append('<Label Content="{0}"/>'.format(label))
                xaml_parts.append('<ComboBox x:Name="{0}"/>'.format(name))

            elif setting_type == "slider":
                # A Slider control paired with a live numeric readout.
                # Supports "min", "max", and "step" (TickFrequency / SmallChange).
                min_val = setting.get("min", 0)
                max_val = setting.get("max", 100)
                step = setting.get("step", 1)
                xaml_parts.append('<Label Content="{0}"/>'.format(label))
                xaml_parts.append('<Grid Margin="0,0,0,4">')
                xaml_parts.append("    <Grid.ColumnDefinitions>")
                xaml_parts.append('        <ColumnDefinition Width="*"/>')
                xaml_parts.append('        <ColumnDefinition Width="46"/>')
                xaml_parts.append("    </Grid.ColumnDefinitions>")
                xaml_parts.append(
                    '    <Slider x:Name="{name}"'
                    ' Grid.Column="0"'
                    ' Minimum="{mn}" Maximum="{mx}"'
                    ' TickFrequency="{step}" SmallChange="{step}"'
                    ' IsSnapToTickEnabled="True"'
                    ' AutoToolTipPlacement="BottomRight"/>'.format(
                        name=name, mn=min_val, mx=max_val, step=step
                    )
                )
                xaml_parts.append(
                    '    <TextBlock x:Name="{0}_display"'
                    ' Grid.Column="1"'
                    ' VerticalAlignment="Center"'
                    ' TextAlignment="Right"'
                    ' Margin="6,0,0,0"'
                    ' FontSize="11"/>'.format(name)
                )
                xaml_parts.append("</Grid>")

            elif setting_type == "color":
                xaml_parts.append('<Label Content="{0}"/>'.format(label))
                xaml_parts.append('<Grid Margin="0,0,0,4">')
                xaml_parts.append("    <Grid.ColumnDefinitions>")
                xaml_parts.append('        <ColumnDefinition Width="30"/>')
                xaml_parts.append('        <ColumnDefinition Width="5"/>')
                xaml_parts.append('        <ColumnDefinition Width="*"/>')
                xaml_parts.append('        <ColumnDefinition Width="Auto"/>')
                xaml_parts.append("    </Grid.ColumnDefinitions>")
                xaml_parts.append(
                    '    <Border x:Name="{0}_preview" Grid.Column="0"'
                    ' BorderBrush="Gray" BorderThickness="1" CornerRadius="2">'.format(name)
                )
                xaml_parts.append('        <Rectangle Fill="White" Height="22"/>')
                xaml_parts.append("    </Border>")
                xaml_parts.append(
                    '    <TextBox x:Name="{0}" Grid.Column="2"/>'.format(name)
                )
                xaml_parts.append(
                    '    <Button x:Name="{0}_button" Grid.Column="3" Content="..."'
                    ' Style="{{StaticResource BrowseButton}}"/>'.format(name)
                )
                xaml_parts.append("</Grid>")

            elif setting_type in ["folder", "file"]:
                xaml_parts.append('<Label Content="{0}"/>'.format(label))
                xaml_parts.append('<Grid Margin="0,0,0,4">')
                xaml_parts.append("    <Grid.ColumnDefinitions>")
                xaml_parts.append('        <ColumnDefinition Width="*"/>')
                xaml_parts.append('        <ColumnDefinition Width="Auto"/>')
                xaml_parts.append("    </Grid.ColumnDefinitions>")
                xaml_parts.append(
                    '    <TextBox x:Name="{0}" Grid.Column="0"/>'.format(name)
                )
                xaml_parts.append(
                    '    <Button x:Name="{0}_button" Grid.Column="1" Content="..."'
                    ' Style="{{StaticResource BrowseButton}}"/>'.format(name)
                )
                xaml_parts.append("</Grid>")

            elif setting_type in ["int", "float", "string"]:
                xaml_parts.append('<Label Content="{0}"/>'.format(label))
                xaml_parts.append('<TextBox x:Name="{0}"/>'.format(name))

        # Footer buttons
        xaml_parts.extend(
            [
                "        </StackPanel>",
                '        <StackPanel Grid.Row="1" Orientation="Horizontal" HorizontalAlignment="Right">',
                '            <Button x:Name="reset_button" Content="Reset" Width="80" Height="30"'
                '                       Margin="0,0,10,0"/>',
                '            <Button x:Name="save_button" Content="Save" Width="80" Height="30"'
                '                       Margin="0,0,10,0" IsDefault="True"/>',
                '            <Button x:Name="cancel_button" Content="Cancel" Width="80" Height="30" IsCancel="True"/>',
                "        </StackPanel>",
                "    </Grid>",
                "</Window>",
            ]
        )

        return "\n".join(xaml_parts)

    # ------------------------------------------------------------------
    # Value population
    # ------------------------------------------------------------------

    def _populate_values(self):
        """Populate controls with current config values."""
        for setting in self.settings_schema:
            setting_type = setting.get("type", "string")

            # Section / separator have no associated control.
            if setting_type in _DISPLAY_ONLY_TYPES:
                continue

            name = setting.get("name")
            default = setting.get("default")
            current_value = self.config.get_option(name, default)

            control = getattr(self, name, None)
            if not control:
                continue

            self.controls[name] = control

            if setting_type == "bool":
                control.IsChecked = bool(current_value)

            elif setting_type == "choice":
                options = setting.get("options", [])
                control.ItemsSource = options
                if current_value in options:
                    control.SelectedItem = current_value
                elif options:
                    control.SelectedIndex = 0

            elif setting_type == "slider":
                try:
                    val = float(current_value) if current_value is not None else float(setting.get("min", 0))
                    # Clamp to declared bounds.
                    min_val = float(setting.get("min", 0))
                    max_val = float(setting.get("max", 100))
                    val = max(min_val, min(max_val, val))
                    control.Value = val
                except (ValueError, TypeError):
                    control.Value = float(setting.get("min", 0))
                # Keep the readout TextBlock in sync as the user drags.
                display = getattr(self, name + "_display", None)
                if display:
                    self._update_slider_display(name)
                    control.ValueChanged += (
                        lambda s, e, n=name: self._on_slider_changed(n)
                    )

            elif setting_type in ["int", "float", "string", "color", "folder", "file"]:
                control.Text = str(current_value) if current_value is not None else ""

                if setting_type == "color":
                    self._update_color_preview(name, control.Text)
                    control.TextChanged += lambda s, e, n=name: self._on_color_text_changed(n)

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

    # ------------------------------------------------------------------
    # Slider helpers
    # ------------------------------------------------------------------

    def _update_slider_display(self, control_name):
        """Refresh the numeric readout next to a slider.

        Args:
            control_name: Name of the slider control
        """
        control = self.controls.get(control_name)
        display = getattr(self, control_name + "_display", None)
        if control and display:
            # Show as int when the value is whole, float otherwise.
            val = control.Value
            if val == int(val):
                display.Text = str(int(val))
            else:
                display.Text = "{0:.2f}".format(val)

    def _on_slider_changed(self, control_name):
        """Handle slider ValueChanged event.

        Args:
            control_name: Name of the slider control
        """
        self._update_slider_display(control_name)

    # ------------------------------------------------------------------
    # Color helpers
    # ------------------------------------------------------------------

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
            self._update_color_preview(control_name, selected_color)

    def _parse_color(self, hex_color):
        """Parse hex color string to WPF Color.

        Args:
            hex_color: Hex color string (e.g., "#FFFF0000" or "#FF0000")

        Returns:
            Color object or None if invalid
        """
        if not hex_color:
            return None
        try:
            hex_color = hex_color.strip()
            if hex_color.startswith("#"):
                hex_color = hex_color[1:]
            if len(hex_color) == 8:
                a = int(hex_color[0:2], 16)
                r = int(hex_color[2:4], 16)
                g = int(hex_color[4:6], 16)
                b = int(hex_color[6:8], 16)
            elif len(hex_color) == 6:
                a = 255
                r = int(hex_color[0:2], 16)
                g = int(hex_color[2:4], 16)
                b = int(hex_color[4:6], 16)
            else:
                return None
            return Color.FromArgb(a, r, g, b)
        except Exception:
            return None

    def _update_color_preview(self, control_name, hex_color):
        """Update the color preview rectangle.

        Args:
            control_name: Name of the color control
            hex_color: Hex color string
        """
        preview = getattr(self, control_name + "_preview", None)
        if not preview:
            return
        color = self._parse_color(hex_color)
        if color:
            if preview.Child:
                preview.Child.Fill = SolidColorBrush(color)
        else:
            if preview.Child:
                preview.Child.Fill = SolidColorBrush(Color.FromArgb(255, 255, 255, 255))

    def _on_color_text_changed(self, control_name):
        """Handle color text box changes to update preview.

        Args:
            control_name: Name of the control
        """
        control = self.controls.get(control_name)
        if control:
            self._update_color_preview(control_name, control.Text)

    # ------------------------------------------------------------------
    # Folder / file helpers
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

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
            min_raw = setting.get("min")
            max_raw = setting.get("max")
            min_val = conversion_func(min_raw) if min_raw is not None else None
            max_val = conversion_func(max_raw) if max_raw is not None else None
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

        elif setting_type == "slider":
            # Slider value is already a float from the control; validate range.
            return self._validate_numeric(setting, value, float, "number")

        elif setting_type in ["string", "color", "folder", "file"]:
            if setting.get("required", False) and not str(value).strip():
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

    # ------------------------------------------------------------------
    # Button handlers
    # ------------------------------------------------------------------

    def save_clicked(self, sender, args):
        """Handle save button click."""
        errors = []
        validated_values = {}

        for setting in self.settings_schema:
            setting_type = setting.get("type", "string")

            # Skip display-only items — no value to read.
            if setting_type in _DISPLAY_ONLY_TYPES:
                continue

            name = setting.get("name")
            control = self.controls.get(name)
            if not control:
                continue

            # Read value from control according to its type.
            if setting_type == "bool":
                value = control.IsChecked
            elif setting_type == "choice":
                value = control.SelectedItem
            elif setting_type == "slider":
                value = control.Value  # float from WPF Slider
            else:
                value = control.Text

            is_valid, validated_value, error_msg = self._validate_setting(
                setting, value
            )

            if not is_valid:
                errors.append(error_msg)
            else:
                validated_values[name] = validated_value

        if errors:
            forms.alert("\n".join(errors), title="Validation Error", warn_icon=True)
            return

        for setting in self.settings_schema:
            name = setting.get("name")
            if name in validated_values:
                self.config.set_option(name, validated_values[name])

        script.save_config()
        self.result = True
        self.Close()

    def cancel_clicked(self, sender, args):
        """Handle cancel button click."""
        self.result = False
        self.Close()

    def reset_clicked(self, sender, args):
        """Handle reset button click."""
        if forms.alert(
            "Are you sure you want to reset all settings, removing it from the .ini?",
            title="Reset Settings",
            yes=True,
            no=True,
        ):
            script.reset_config(self.config_section)
            self.result = False
            self.Close()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def show_settings(settings_schema, section=None, title="Settings", width=450):
    """Show settings window and return True if saved.

    Args:
        settings_schema: List of setting definitions. Each entry is a dict with:

            Structural / display-only (no "name" key required):
            - type "section"   -- bold heading + separator line.  Requires "label".
            - type "separator" -- bare horizontal rule, no label.

            Interactive settings (all require "name"):
            - type "bool"      -- CheckBox.
            - type "choice"    -- ComboBox. Requires "options" list.
            - type "slider"    -- Slider with live readout. Supports "min", "max", "step".
            - type "int"       -- TextBox validated as integer. Supports "min", "max".
            - type "float"     -- TextBox validated as float.  Supports "min", "max".
            - type "string"    -- TextBox. Supports "required" (bool).
            - type "color"     -- TextBox + color-preview swatch + picker button.
            - type "folder"    -- TextBox + folder-browse button.
            - type "file"      -- TextBox + file-browse button.
                                  Supports "file_ext", "files_filter", "init_dir",
                                  "multi_file".

            Common optional keys for interactive settings:
            - name (str):     Setting key stored in .ini config.
            - label (str):    Human-readable label shown in the UI.
            - default:        Value used when no config entry exists yet.
            - required (bool): For "string" / path types — blocks save if empty.

        section (str): Config section name (default: None)
        title (str):   Window title (default: "Settings")
        width (int):   Window width in pixels (default: 450)

    Returns:
        bool: True if settings were saved, False if canceled/reset.

    Example::

        settings_schema = [
            {"type": "section", "label": "Display"},
            {"name": "scope", "type": "choice", "label": "Scope",
             "options": ["Visibility", "Active State"], "default": "Visibility"},
            {"name": "highlight_color", "type": "color", "label": "Highlight Color",
             "default": "#ffff0000"},

            {"type": "section", "label": "Processing"},
            {"name": "tolerance", "type": "slider", "label": "Tolerance (mm)",
             "default": 10, "min": 0, "max": 1000, "step": 5},
            {"name": "set_workset", "type": "bool", "label": "Set Workset",
             "default": True},

            {"type": "separator"},

            {"name": "prefix", "type": "string", "label": "Prefix", "default": ""},
        ]

        if show_settings(settings_schema, section="MyToolSection", title="My Tool Settings"):
            print("Settings saved!")
    """
    window = SettingsWindow(settings_schema, section, title, width)
    window.ShowDialog()
    return window.result
