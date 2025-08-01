# -*- coding: UTF-8 -*-
from pyrevit import forms, script


class CoordinateSystemSelector(forms.WPFWindow):
    """Custom window for selecting coordinate system and angle tolerance."""

    def __init__(self, xaml_source):
        super(CoordinateSystemSelector, self).__init__(xaml_source)

        # Result storage
        self.result = None

        # Find controls
        self.radio_internal = self.FindName("radio_internal")
        self.radio_project = self.FindName("radio_project")
        self.radio_view = self.FindName("radio_view")
        self.angle_slider = self.FindName("angle_slider")
        self.angle_display = self.FindName("angle_display")
        self.angle_description = self.FindName("angle_description")

        # Set initial values
        self.radio_internal.IsChecked = True
        self.angle_slider.Value = 10
        self.update_angle_display()

    def update_angle_display(self):
        """Update the angle display and description based on slider value."""
        angle = int(self.angle_slider.Value)
        self.angle_display.Text = "{}°".format(angle)

        # Angle descriptions
        descriptions = {
            1: "Very strict - only perfectly aligned grids",
            5: "Tight - good for precise grid layouts",
            10: "Moderate - good for most cases",
            15: "Relaxed - includes slightly angled grids",
            25: "Permissive - includes more angled grids",
            35: "Very permissive - includes most orientations",
            40: "Maximum tolerance - includes heavily angled grids"
        }

        # Find closest description
        closest_angle = min(descriptions.keys(), key=lambda x: abs(x - angle))
        self.angle_description.Text = descriptions[closest_angle]

    def angle_slider_changed(self, sender, args):
        """Handle slider value change."""
        self.update_angle_display()

    def get_selected_coordinate_system(self):
        """Get the selected coordinate system."""
        if self.radio_internal.IsChecked:
            return 'internal'
        elif self.radio_project.IsChecked:
            return 'project'
        elif self.radio_view.IsChecked:
            return 'view'
        return 'internal'  # fallback

    def proceed(self, sender, args):
        """Handle Continue button click."""
        self.result = {
            'coordinate_system': self.get_selected_coordinate_system(),
            'angle_tolerance': int(self.angle_slider.Value)
        }
        self.Close()

    def cancel(self, sender, args):
        """Handle Cancel button click."""
        self.result = None
        self.Close()

    def move_window(self, sender, args):
        """Allow window dragging."""
        self.DragMove()


def show_coordinate_system_selector():
    """Show the coordinate system selector dialog and return user selection."""

    # Load XAML file using pyRevit's method (same as your main script)
    xamlfile = script.get_bundle_file("coordinate_selector_ui.xaml")

    # Create and show dialog
    dialog = CoordinateSystemSelector(xamlfile)
    dialog.ShowDialog()

    return dialog.result
