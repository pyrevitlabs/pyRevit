"""Configuration window for Match tool."""
#pylint: disable=E0401,C0111,W0613
from pyrevit import HOST_APP
from pyrevit import forms
from pyrevit import script


class MatchPropConfigWindow(forms.WPFWindow):
    def __init__(self, xaml_file_name):
        forms.WPFWindow.__init__(self, xaml_file_name)

        self._config = script.get_config()

        # base
        self.halftone.IsChecked = \
            self._config.get_option('halftone', True)
        self.transparency.IsChecked = \
            self._config.get_option('transparency', True)

        # projection lines
        self.proj_line_color.IsChecked = \
            self._config.get_option('proj_line_color', True)
        self.proj_line_pattern.IsChecked = \
            self._config.get_option('proj_line_pattern', True)
        self.proj_line_weight.IsChecked = \
            self._config.get_option('proj_line_weight', True)

        # projection forground pattern
        self.proj_fill_color.IsChecked = \
            self._config.get_option('proj_fill_color', True)
        self.proj_fill_pattern.IsChecked = \
            self._config.get_option('proj_fill_pattern', True)
        self.proj_fill_pattern_visibility.IsChecked = \
            self._config.get_option('proj_fill_pattern_visibility', True)

        # projection background pattern (Revit >= 2019)
        if HOST_APP.is_newer_than(2019, or_equal=True):
            self.proj_bg_fill_color.IsChecked = \
                self._config.get_option('proj_bg_fill_color', True)
            self.proj_bg_fill_pattern.IsChecked = \
                self._config.get_option('proj_bg_fill_pattern', True)
            self.proj_bg_fill_pattern_visibility.IsChecked = \
                self._config.get_option('proj_bg_fill_pattern_visibility', True)

        # cut lines
        self.cut_line_color.IsChecked = \
            self._config.get_option('cut_line_color', True)
        self.cut_line_pattern.IsChecked = \
            self._config.get_option('cut_line_pattern', True)
        self.cut_line_weight.IsChecked = \
            self._config.get_option('cut_line_weight', True)

        # cut forground pattern
        self.cut_fill_color.IsChecked = \
            self._config.get_option('cut_fill_color', True)
        self.cut_fill_pattern.IsChecked = \
            self._config.get_option('cut_fill_pattern', True)
        self.cut_fill_pattern_visibility.IsChecked = \
            self._config.get_option('cut_fill_pattern_visibility', True)

        # cut background pattern (Revit >= 2019)
        if HOST_APP.is_newer_than(2019, or_equal=True):
            self.cut_bg_fill_color.IsChecked = \
                self._config.get_option('cut_bg_fill_color', True)
            self.cut_bg_fill_pattern.IsChecked = \
                self._config.get_option('cut_bg_fill_pattern', True)
            self.cut_bg_fill_pattern_visibility.IsChecked = \
                self._config.get_option('cut_bg_fill_pattern_visibility', True)

        # dim overrides
        self.dim_override.IsChecked = \
            self._config.get_option('dim_override', True)
        self.dim_textposition.IsChecked = \
            self._config.get_option('dim_textposition', False)
        self.dim_above.IsChecked = self._config.get_option('dim_above', True)
        self.dim_below.IsChecked = self._config.get_option('dim_below', True)
        self.dim_prefix.IsChecked = self._config.get_option('dim_prefix', True)
        self.dim_suffix.IsChecked = self._config.get_option('dim_suffix', True)

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
        self.proj_bg_fill_color.IsChecked = state
        self.proj_bg_fill_pattern.IsChecked = state
        self.proj_bg_fill_pattern_visibility.IsChecked = state
        self.cut_line_color.IsChecked = state
        self.cut_line_pattern.IsChecked = state
        self.cut_line_weight.IsChecked = state
        self.cut_fill_color.IsChecked = state
        self.cut_fill_pattern.IsChecked = state
        self.cut_fill_pattern_visibility.IsChecked = state
        self.cut_bg_fill_color.IsChecked = state
        self.cut_bg_fill_pattern.IsChecked = state
        self.cut_bg_fill_pattern_visibility.IsChecked = state

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
        # base
        self._config.halftone = self.halftone.IsChecked
        self._config.transparency = self.transparency.IsChecked

        # projection lines
        self._config.proj_line_color = self.proj_line_color.IsChecked
        self._config.proj_line_pattern = self.proj_line_pattern.IsChecked
        self._config.proj_line_weight = self.proj_line_weight.IsChecked

        # projection forground pattern
        self._config.proj_fill_color = self.proj_fill_color.IsChecked
        self._config.proj_fill_pattern = self.proj_fill_pattern.IsChecked
        self._config.proj_fill_pattern_visibility = \
            self.proj_fill_pattern_visibility.IsChecked

        # projection background pattern (Revit >= 2019)
        if HOST_APP.is_newer_than(2019, or_equal=True):
            self._config.proj_bg_fill_color = \
                self.proj_bg_fill_color.IsChecked
            self._config.proj_bg_fill_pattern = \
                self.proj_bg_fill_pattern.IsChecked
            self._config.proj_bg_fill_pattern_visibility = \
                self.proj_bg_fill_pattern_visibility.IsChecked

        # cut lines
        self._config.cut_line_color = self.cut_line_color.IsChecked
        self._config.cut_line_pattern = self.cut_line_pattern.IsChecked
        self._config.cut_line_weight = self.cut_line_weight.IsChecked

        # cut forground pattern
        self._config.cut_fill_color = self.cut_fill_color.IsChecked
        self._config.cut_fill_pattern = self.cut_fill_pattern.IsChecked
        self._config.cut_fill_pattern_visibility = \
            self.cut_fill_pattern_visibility.IsChecked

        # cut background pattern (Revit >= 2019)
        if HOST_APP.is_newer_than(2019, or_equal=True):
            self._config.cut_bg_fill_color = \
                self.cut_bg_fill_color.IsChecked
            self._config.cut_bg_fill_pattern = \
                self.cut_bg_fill_pattern.IsChecked
            self._config.cut_bg_fill_pattern_visibility = \
                self.cut_bg_fill_pattern_visibility.IsChecked

        # dim overrides
        self._config.dim_override = self.dim_override.IsChecked
        self._config.dim_textposition = self.dim_textposition.IsChecked
        self._config.dim_above = self.dim_above.IsChecked
        self._config.dim_below = self.dim_below.IsChecked
        self._config.dim_prefix = self.dim_prefix.IsChecked
        self._config.dim_suffix = self.dim_suffix.IsChecked

        script.save_config()
        self.Close()


if HOST_APP.is_newer_than(2019, or_equal=True):
    MatchPropConfigWindow('MatchConfigWindow.xaml').ShowDialog()
else:
    MatchPropConfigWindow('MatchConfigWindowLegacy.xaml').ShowDialog()
