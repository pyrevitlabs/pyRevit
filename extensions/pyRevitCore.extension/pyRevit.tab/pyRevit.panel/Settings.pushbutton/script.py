import os

from pyrevit import HOST_APP
from pyrevit.coreutils import filter_null_items
from pyrevit.coreutils.envvars import get_pyrevit_env_vars
from pyrevit.loader.addin.addinfiles import get_addinfiles_state, set_addinfiles_state
from pyrevit.userconfig import user_config
from scriptutils import logger, show_file_in_explorer
from scriptutils.userinput import WPFWindow, pick_folder

# noinspection PyUnresolvedReferences
from System.Windows.Forms import Clipboard


__doc__ = 'Shows the preferences window for pyrevit. You can customize how pyrevit loads and set some basic '\
          'parameters here.\n\nShift-Click: Shows config file in explorer.'


class SettingsWindow(WPFWindow):
    def __init__(self, xaml_file_name):
        WPFWindow.__init__(self, xaml_file_name)
        try:
            self._setup_core_options()
        except Exception as setup_params_err:
            logger.error('Error setting up a parameter. Please update pyRevit again. | {}'.format(setup_params_err))

        self._setup_user_extensions_list()
        self._setup_env_vars_list()
        self._addinfiles_checkboxes = {'2015': self.revit2015_cb,
                                       '2016': self.revit2016_cb,
                                       '2017': self.revit2017_cb}

        self._setup_addinfiles()

    def _setup_core_options(self):
        self.checkupdates_cb.IsChecked = user_config.core.checkupdates

        if not user_config.core.verbose and not user_config.core.debug:
            self.noreporting_rb.IsChecked = True
        else:
            self.debug_rb.IsChecked = user_config.core.debug
            self.verbose_rb.IsChecked = user_config.core.verbose

        self.filelogging_cb.IsChecked = user_config.core.filelogging

        self.startup_log_timeout.Text = str(user_config.core.startuplogtimeout)
        self.compilecsharp_cb.IsChecked = user_config.core.compilecsharp
        self.compilevb_cb.IsChecked = user_config.core.compilevb

        if user_config.core.bincache:
            self.bincache_rb.IsChecked = True
        else:
            self.asciicache_rb.IsChecked = True

        self.loadbetatools_cb.IsChecked = user_config.core.get_option('loadbeta', default_value=False)

    def _setup_user_extensions_list(self):
        self.extfolders_lb.ItemsSource = user_config.core.userextensions

    def _setup_env_vars_list(self):
        class EnvVariable:
            def __init__(self, var_id, value):
                self.Id = var_id
                self.Value = value

        env_vars_list = [EnvVariable(k, v) for k, v in get_pyrevit_env_vars().items()]

        self.envvars_lb.ItemsSource = env_vars_list

    def _setup_addinfiles(self):
        addinfiles_states = get_addinfiles_state()

        for rvt_ver, checkbox in self._addinfiles_checkboxes.items():
            if rvt_ver in addinfiles_states.keys():
                if rvt_ver != HOST_APP.version:
                    checkbox.IsEnabled = True
                    checkbox.IsChecked = addinfiles_states[rvt_ver]
                else:
                    checkbox.Content = 'Revit {} (Current version. Can not disable.)'.format(rvt_ver)
                    checkbox.IsEnabled = False
                    checkbox.IsChecked = True
            else:
                checkbox.Content = 'Revit {} (Not installed)'.format(rvt_ver)
                checkbox.IsChecked = checkbox.IsEnabled = False

    def update_addinfiles(self):
        new_states = {rvt_ver: checkbox.IsChecked for rvt_ver, checkbox in self._addinfiles_checkboxes.items()}
        new_states.pop(HOST_APP.version)
        set_addinfiles_state(new_states)

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def resetreportinglevel(self, sender, args):
        self.verbose_rb.IsChecked = True
        self.noreporting_rb.IsChecked = False
        self.debug_rb.IsChecked = False
        self.filelogging_cb.IsChecked = False

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def resetcache(self, sender, args):
        self.bincache_rb.IsChecked = True

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def copy_envvar_value(self, sender, args):
        Clipboard.SetText(self.envvars_lb.SelectedItem.Value)

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def copy_envvar_id(self, sender, args):
        Clipboard.SetText(self.envvars_lb.SelectedItem.Id)

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
        user_config.core.loadbeta = self.loadbetatools_cb.IsChecked
        user_config.core.startuplogtimeout = self.startup_log_timeout.Text

        if isinstance(self.extfolders_lb.ItemsSource, list):
            user_config.core.userextensions = filter_null_items(self.extfolders_lb.ItemsSource)
        else:
            user_config.core.userextensions = []

        user_config.save_changes()

        self.update_addinfiles()
        self.Close()


if __name__ == '__main__':
    # noinspection PyUnresolvedReferences
    if __shiftclick__:
        show_file_in_explorer(user_config.config_file)
    else:
        SettingsWindow('SettingsWindow.xaml').ShowDialog()
