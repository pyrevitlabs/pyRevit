import clr
import os

from pyrevit.userconfig import user_config
from pyrevit.coreutils.logger import get_logger

clr.AddReference('PresentationCore')
clr.AddReferenceByPartialName("PresentationFramework")
clr.AddReference('IronPython.Wpf')

# noinspection PyUnresolvedReferences
from System.Windows import Window
# noinspection PyUnresolvedReferences
import wpf

folder = os.path.dirname(__file__)
logger = get_logger(__name__)


class MyWindow(Window):
    def __init__(self):
        wpf.LoadComponent(self, os.path.join(folder, 'MatchConfigWindow.xaml'))
        try:
            self.halftone.IsChecked = user_config.matchpropoptions.halftone
            self.transparency.IsChecked = user_config.matchpropoptions.transparency
            self.proj_line_color.IsChecked = user_config.matchpropoptions.proj_line_color
            self.proj_line_pattern.IsChecked = user_config.matchpropoptions.proj_line_pattern
            self.proj_line_weight.IsChecked = user_config.matchpropoptions.proj_line_weight
            self.proj_fill_color.IsChecked = user_config.matchpropoptions.proj_fill_color
            self.proj_fill_pattern.IsChecked = user_config.matchpropoptions.proj_fill_pattern
            self.proj_fill_pattern_visibility.IsChecked = user_config.matchpropoptions.proj_fill_pattern_visibility
            self.cut_line_color.IsChecked = user_config.matchpropoptions.cut_line_color
            self.cut_line_pattern.IsChecked = user_config.matchpropoptions.cut_line_pattern
            self.cut_line_weight.IsChecked = user_config.matchpropoptions.cut_line_weight
            self.cut_fill_color.IsChecked = user_config.matchpropoptions.cut_fill_color
            self.cut_fill_pattern.IsChecked = user_config.matchpropoptions.cut_fill_pattern
            self.cut_fill_pattern_visibility.IsChecked = user_config.matchpropoptions.cut_fill_pattern_visibility
        except:
            try:
                user_config.add_section('matchpropoptions')
            except Exception as sec_err:
                logger.debug('Matchpropoptions error. | {}'.format(sec_err))

            user_config.matchpropoptions.halftone = True
            user_config.matchpropoptions.transparency = True
            user_config.matchpropoptions.proj_line_color = True
            user_config.matchpropoptions.proj_line_pattern = True
            user_config.matchpropoptions.proj_line_weight = True
            user_config.matchpropoptions.proj_fill_color = True
            user_config.matchpropoptions.proj_fill_pattern = True
            user_config.matchpropoptions.proj_fill_pattern_visibility = True
            user_config.matchpropoptions.cut_line_color = True
            user_config.matchpropoptions.cut_line_pattern = True
            user_config.matchpropoptions.cut_line_weight = True
            user_config.matchpropoptions.cut_fill_color = True
            user_config.matchpropoptions.cut_fill_pattern = True
            user_config.matchpropoptions.cut_fill_pattern_visibility = True
            user_config.save_changes()

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
        user_config.matchpropoptions.halftone = self.halftone.IsChecked
        user_config.matchpropoptions.transparency = self.transparency.IsChecked
        user_config.matchpropoptions.proj_line_color = self.proj_line_color.IsChecked
        user_config.matchpropoptions.proj_line_pattern = self.proj_line_pattern.IsChecked
        user_config.matchpropoptions.proj_line_weight = self.proj_line_weight.IsChecked
        user_config.matchpropoptions.proj_fill_color = self.proj_fill_color.IsChecked
        user_config.matchpropoptions.proj_fill_pattern = self.proj_fill_pattern.IsChecked
        user_config.matchpropoptions.proj_fill_pattern_visibility = self.proj_fill_pattern_visibility.IsChecked
        user_config.matchpropoptions.cut_line_color = self.cut_line_color.IsChecked
        user_config.matchpropoptions.cut_line_pattern = self.cut_line_pattern.IsChecked
        user_config.matchpropoptions.cut_line_weight = self.cut_line_weight.IsChecked
        user_config.matchpropoptions.cut_fill_color = self.cut_fill_color.IsChecked
        user_config.matchpropoptions.cut_fill_pattern = self.cut_fill_pattern.IsChecked
        user_config.matchpropoptions.cut_fill_pattern_visibility = self.cut_fill_pattern_visibility.IsChecked

        user_config.save_changes()
        self.Close()


if __name__ == '__main__':
    MyWindow().ShowDialog()
