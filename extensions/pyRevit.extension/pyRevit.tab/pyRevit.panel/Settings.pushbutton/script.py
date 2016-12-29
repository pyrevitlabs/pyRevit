import os

from pyrevit.coreutils.envvars import get_pyrevit_env_vars
from pyrevit.userconfig import user_config
from scriptutils import logger, show_file_in_explorer
from scriptutils.userinput import WPFWindow, pick_folder


__doc__ = 'Shows the preferences window for pyrevit. You can customize how pyrevit loads and set some basic '\
          'parameters here.\n\nShift-Click: Shows config file in explorer.'


class SettingsWindow(WPFWindow):
    def __init__(self, xaml_file_name):
        WPFWindow.__init__(self, xaml_file_name)

        self.checkupdates_cb.IsChecked = user_config.core.checkupdates
        self.verbose_rb.IsChecked = user_config.core.verbose
        self.debug_rb.IsChecked = user_config.core.debug
        self.filelogging_cb.IsChecked = user_config.core.filelogging
        self.compilecsharp_cb.IsChecked = user_config.core.compilecsharp
        self.compilevb_cb.IsChecked = user_config.core.compilevb

        if user_config.core.bincache:
            self.bincache_rb.IsChecked = True
        else:
            self.asciicache_rb.IsChecked = True

        self.extfolders_lb.ItemsSource = user_config.core.userextensions

        class EnvVariable:
            def __init__(self, id, value):
                self.Id = id
                self.Value = value

        env_vars_list = [EnvVariable(k,v) for k,v in get_pyrevit_env_vars().items()]

        self.envvars_lb.ItemsSource = env_vars_list

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def resetreportinglevel(self, sender, args):
        self.verbose_rb.IsChecked = True
        self.debug_rb.IsChecked = False
        self.filelogging_cb.IsChecked = False

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def resetcache(self, sender, args):
        self.bincache_rb.IsChecked = True

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def addfolder(self, sender, args):
        new_path = pick_folder()

        if new_path:
            new_path = os.path.normpath(new_path)

        if self.extfolders_lb.ItemsSource:
            uniq_items = set(self.extfolders_lb.ItemsSource)
            uniq_items.add(new_path)
            self.extfolders_lb.ItemsSource = list(uniq_items)
        else:
            self.extfolders_lb.ItemsSource = [new_path]

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def removefolder(self, sender, args):
        selected_path = self.extfolders_lb.SelectedItem
        if self.extfolders_lb.ItemsSource:
            uniq_items = set(self.extfolders_lb.ItemsSource)
            uniq_items.remove(selected_path)
            self.extfolders_lb.ItemsSource = list(uniq_items)

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def removeallfolders(self, sender, args):
        self.extfolders_lb.ItemsSource = []

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def savesettings(self, sender, args):
        if self.verbose_rb.IsChecked:
            logger.set_verbose_mode()
        if self.debug_rb.IsChecked:
            logger.set_debug_mode()

        user_config.core.checkupdates = self.checkupdates_cb.IsChecked
        user_config.core.verbose = self.verbose_rb.IsChecked
        user_config.core.debug = self.debug_rb.IsChecked
        user_config.core.filelogging = self.filelogging_cb.IsChecked
        user_config.core.bincache = self.bincache_rb.IsChecked
        user_config.core.compilecsharp = self.compilecsharp_cb.IsChecked
        user_config.core.compilevb = self.compilevb_cb.IsChecked

        if isinstance(self.extfolders_lb.ItemsSource, list):
            user_config.core.userextensions = self.extfolders_lb.ItemsSource
        else:
            user_config.core.userextensions = []

        user_config.save_changes()
        self.Close()


if __name__ == '__main__':
    # noinspection PyUnresolvedReferences
    if __shiftclick__:
        show_file_in_explorer(user_config.config_file)
    else:
        SettingsWindow('SettingsWindow.xaml').ShowDialog()
