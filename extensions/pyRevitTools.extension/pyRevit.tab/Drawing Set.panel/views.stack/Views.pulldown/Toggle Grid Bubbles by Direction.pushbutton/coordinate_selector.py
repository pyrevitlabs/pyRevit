# -*- coding: UTF-8 -*-
from System import Windows
from pyrevit import forms, script


class CoordinateSystemSelector(forms.WPFWindow):
    """Custom window for selecting coordinate system and angle tolerance."""

    def __init__(self, xaml_source):
        super(CoordinateSystemSelector, self).__init__(xaml_source)

        # Result storage
        self.result = None

        # Find controls
        self.all_grids = self.FindName("all_grids")
        self.radio_true_north = self.FindName("radio_true_north")
        self.radio_project_north = self.FindName("radio_project_north")
        self.radio_view_orientation = self.FindName("radio_view_orientation")
        self.angle_slider = self.FindName("angle_slider")
        self.angle_display = self.FindName("angle_display")
        self.angle_description = self.FindName("angle_description")

        # Set initial values
        self.all_grids.IsChecked = True
        self.angle_slider.Value = 1
        self.update_angle_display()

    def update_angle_display(self):
        """Update the angle display and description based on slider value."""
        angle = int(self.angle_slider.Value)
        self.angle_display.Text = "{}°".format(angle)

        # Angle descriptions - using translated strings from resource dictionary
        descriptions = {
            1: self.get_locale_string("AngleDescription1"),
            5: self.get_locale_string("AngleDescription5"),
            10: self.get_locale_string("AngleDescription10"),
            15: self.get_locale_string("AngleDescription15"),
            25: self.get_locale_string("AngleDescription25"),
            35: self.get_locale_string("AngleDescription35"),
            40: self.get_locale_string("AngleDescription40"),
        }

        # Find closest description
        closest_angle = min(descriptions.keys(), key=lambda x: abs(x - angle))
        self.angle_description.Text = descriptions[closest_angle]

    def angle_slider_changed(self, sender, args):
        """Handle slider value change."""
        self.update_angle_display()

    def get_selected_coordinate_system(self):
        """Get the selected coordinate system."""
        if self.all_grids.IsChecked:
            return "all_grids"
        elif self.radio_true_north.IsChecked:
            return "true_north"
        elif self.radio_project_north.IsChecked:
            return "project_north"
        elif self.radio_view_orientation.IsChecked:
            return "view"
        return "true_north"  # fallback

    def proceed(self, sender, args):
        """Handle Continue button click."""
        self.result = {
            "coordinate_system": self.get_selected_coordinate_system(),
            "angle_tolerance": int(self.angle_slider.Value),
            "window_left": self.Left,
            "window_top": self.Top,
        }
        self.Close()

    def cancel(self, sender, args):
        """Handle Cancel button click."""
        self.result = None
        self.Close()

    def move_window(self, sender, args):
        """Allow window dragging."""
        self.DragMove()


def show_coordinate_system_selector(
    previous_system=None, previous_tolerance=None, window_left=None, window_top=None
):
    """Show the coordinate system selector dialog and return user selection."""

    # Load XAML file using pyRevit's method (same as your main script)
    xamlfile = script.get_bundle_file("coordinate_selector_ui.xaml")

    # Create and show dialog
    dialog = CoordinateSystemSelector(xamlfile)

    if previous_system:
        if previous_system == "true_north":
            dialog.radio_true_north.IsChecked = True
        elif previous_system == "project_north":
            dialog.radio_project_north.IsChecked = True
        elif previous_system == "view":
            dialog.radio_view_orientation.IsChecked = True

    if previous_tolerance:
        dialog.angle_slider.Value = previous_tolerance
        dialog.update_angle_display()

    if window_left is not None and window_top is not None:
        dialog.WindowStartupLocation = Windows.WindowStartupLocation.Manual
        dialog.Left = window_left
        dialog.Top = window_top

    dialog.ShowDialog()

    return dialog.result
