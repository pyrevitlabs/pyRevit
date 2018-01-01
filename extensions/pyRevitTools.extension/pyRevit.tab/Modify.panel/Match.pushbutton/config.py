from pyrevit import forms
from pyrevit import script


my_config = script.get_config()


class MatchPropConfigWindow(forms.WPFWindow):
    def __init__(self, xaml_file_name):
        forms.WPFWindow.__init__(self, xaml_file_name)

        try:
            self.halftone.IsChecked = my_config.halftone
            self.transparency.IsChecked = my_config.transparency
            self.proj_line_color.IsChecked = my_config.proj_line_color
            self.proj_line_pattern.IsChecked = my_config.proj_line_pattern
            self.proj_line_weight.IsChecked = my_config.proj_line_weight
            self.proj_fill_color.IsChecked = my_config.proj_fill_color
            self.proj_fill_pattern.IsChecked = my_config.proj_fill_pattern
            self.proj_fill_pattern_visibility.IsChecked = \
                my_config.proj_fill_pattern_visibility
            self.cut_line_color.IsChecked = my_config.cut_line_color
            self.cut_line_pattern.IsChecked = my_config.cut_line_pattern
            self.cut_line_weight.IsChecked = my_config.cut_line_weight
            self.cut_fill_color.IsChecked = my_config.cut_fill_color
            self.cut_fill_pattern.IsChecked = my_config.cut_fill_pattern
            self.cut_fill_pattern_visibility.IsChecked = \
                my_config.cut_fill_pattern_visibility

            self.dim_override.IsChecked = my_config.dim_override
            self.dim_textposition.IsChecked = my_config.dim_textposition
            self.dim_above.IsChecked = my_config.dim_above
            self.dim_below.IsChecked = my_config.dim_below
            self.dim_prefix.IsChecked = my_config.dim_prefix
            self.dim_suffix.IsChecked = my_config.dim_suffix

        except:
            self.halftone.IsChecked = my_config.halftone = True
            self.transparency.IsChecked = my_config.transparency = True
            self.proj_line_color.IsChecked = my_config.proj_line_color = True
            self.proj_line_pattern.IsChecked = \
                my_config.proj_line_pattern = True
            self.proj_line_weight.IsChecked = my_config.proj_line_weight = True
            self.proj_fill_color.IsChecked = my_config.proj_fill_color = True
            self.proj_fill_pattern.IsChecked = \
                my_config.proj_fill_pattern = True
            self.proj_fill_pattern_visibility.IsChecked = \
                my_config.proj_fill_pattern_visibility = True
            self.cut_line_color.IsChecked = my_config.cut_line_color = True
            self.cut_line_pattern.IsChecked = my_config.cut_line_pattern = True
            self.cut_line_weight.IsChecked = my_config.cut_line_weight = True
            self.cut_fill_color.IsChecked = my_config.cut_fill_color = True
            self.cut_fill_pattern.IsChecked = my_config.cut_fill_pattern = True
            self.cut_fill_pattern_visibility.IsChecked = \
                my_config.cut_fill_pattern_visibility = True

            self.dim_override.IsChecked = my_config.dim_override = True
            self.dim_textposition.IsChecked = \
                my_config.dim_textposition = False
            self.dim_above.IsChecked = my_config.dim_above = True
            self.dim_below.IsChecked = my_config.dim_below = True
            self.dim_prefix.IsChecked = my_config.dim_prefix = True
            self.dim_suffix.IsChecked = my_config.dim_suffix = True

            script.save_config()

    def set_all(self, state):
        self.halftone.IsChecked = state
        self.transparency.IsChecked = state
        self.proj_line_color.IsChecked = state
        self.proj_line_pattern.IsChecked = state
        self.proj_line_weight.IsChecked = state
        self.proj_fill_color.IsChecked = state
        self.proj_fill_pattern.IsChecked = state
        self.proj_fill_pattern_visibility.IsChecked = state
        self.cut_line_color.IsChecked = state
        self.cut_line_pattern.IsChecked = state
        self.cut_line_weight.IsChecked = state
        self.cut_fill_color.IsChecked = state
        self.cut_fill_pattern.IsChecked = state
        self.cut_fill_pattern_visibility.IsChecked = state

        self.dim_override.IsChecked = state
        self.dim_textposition.IsChecked = state
        self.dim_above.IsChecked = state
        self.dim_below.IsChecked = state
        self.dim_prefix.IsChecked = state
        self.dim_suffix.IsChecked = state

    def check_all(self, sender, args):
        self.set_all(True)

    def check_none(self, sender, args):
        self.set_all(False)

    def save_options(self, sender, args):
        my_config.halftone = self.halftone.IsChecked
        my_config.transparency = self.transparency.IsChecked
        my_config.proj_line_color = self.proj_line_color.IsChecked
        my_config.proj_line_pattern = self.proj_line_pattern.IsChecked
        my_config.proj_line_weight = self.proj_line_weight.IsChecked
        my_config.proj_fill_color = self.proj_fill_color.IsChecked
        my_config.proj_fill_pattern = self.proj_fill_pattern.IsChecked
        my_config.proj_fill_pattern_visibility = \
            self.proj_fill_pattern_visibility.IsChecked
        my_config.cut_line_color = self.cut_line_color.IsChecked
        my_config.cut_line_pattern = self.cut_line_pattern.IsChecked
        my_config.cut_line_weight = self.cut_line_weight.IsChecked
        my_config.cut_fill_color = self.cut_fill_color.IsChecked
        my_config.cut_fill_pattern = self.cut_fill_pattern.IsChecked
        my_config.cut_fill_pattern_visibility = \
            self.cut_fill_pattern_visibility.IsChecked

        my_config.dim_override = self.dim_override.IsChecked
        my_config.dim_textposition = self.dim_textposition.IsChecked
        my_config.dim_above = self.dim_above.IsChecked
        my_config.dim_below = self.dim_below.IsChecked
        my_config.dim_prefix = self.dim_prefix.IsChecked
        my_config.dim_suffix = self.dim_suffix.IsChecked

        script.save_config()
        self.Close()


MatchPropConfigWindow('MatchConfigWindow.xaml').ShowDialog()
