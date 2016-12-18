from scriptutils import logger, my_config, save_my_config
from scriptutils.userinput import WPFWindow


class MatchPropConfigWindow(WPFWindow):
    def __init__(self, xaml_file_name):
        WPFWindow.__init__(self, xaml_file_name)

        try:
            self.halftone.IsChecked = my_config.halftone
            self.transparency.IsChecked = my_config.transparency
            self.proj_line_color.IsChecked = my_config.proj_line_color
            self.proj_line_pattern.IsChecked = my_config.proj_line_pattern
            self.proj_line_weight.IsChecked = my_config.proj_line_weight
            self.proj_fill_color.IsChecked = my_config.proj_fill_color
            self.proj_fill_pattern.IsChecked = my_config.proj_fill_pattern
            self.proj_fill_pattern_visibility.IsChecked = my_config.proj_fill_pattern_visibility
            self.cut_line_color.IsChecked = my_config.cut_line_color
            self.cut_line_pattern.IsChecked = my_config.cut_line_pattern
            self.cut_line_weight.IsChecked = my_config.cut_line_weight
            self.cut_fill_color.IsChecked = my_config.cut_fill_color
            self.cut_fill_pattern.IsChecked = my_config.cut_fill_pattern
            self.cut_fill_pattern_visibility.IsChecked = my_config.cut_fill_pattern_visibility
        except:
            my_config.halftone = True
            my_config.transparency = True
            my_config.proj_line_color = True
            my_config.proj_line_pattern = True
            my_config.proj_line_weight = True
            my_config.proj_fill_color = True
            my_config.proj_fill_pattern = True
            my_config.proj_fill_pattern_visibility = True
            my_config.cut_line_color = True
            my_config.cut_line_pattern = True
            my_config.cut_line_weight = True
            my_config.cut_fill_color = True
            my_config.cut_fill_pattern = True
            my_config.cut_fill_pattern_visibility = True
            save_my_config()

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

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def check_all(self, sender, args):
        self.set_all(True)

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def check_none(self, sender, args):
        self.set_all(False)

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def save_options(self, sender, args):
        my_config.halftone = self.halftone.IsChecked
        my_config.transparency = self.transparency.IsChecked
        my_config.proj_line_color = self.proj_line_color.IsChecked
        my_config.proj_line_pattern = self.proj_line_pattern.IsChecked
        my_config.proj_line_weight = self.proj_line_weight.IsChecked
        my_config.proj_fill_color = self.proj_fill_color.IsChecked
        my_config.proj_fill_pattern = self.proj_fill_pattern.IsChecked
        my_config.proj_fill_pattern_visibility = self.proj_fill_pattern_visibility.IsChecked
        my_config.cut_line_color = self.cut_line_color.IsChecked
        my_config.cut_line_pattern = self.cut_line_pattern.IsChecked
        my_config.cut_line_weight = self.cut_line_weight.IsChecked
        my_config.cut_fill_color = self.cut_fill_color.IsChecked
        my_config.cut_fill_pattern = self.cut_fill_pattern.IsChecked
        my_config.cut_fill_pattern_visibility = self.cut_fill_pattern_visibility.IsChecked

        save_my_config()
        self.Close()


if __name__ == '__main__':
    MatchPropConfigWindow('MatchConfigWindow.xaml').ShowDialog()
