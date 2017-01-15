"""Add or remove pyRevit extensions."""

from pyrevit.coreutils import open_folder_in_explorer
from pyrevit.plugins import extpackages
from pyrevit.userconfig import user_config

from scriptutils import logger
from scriptutils import open_url
from scriptutils.userinput import WPFWindow

# noinspection PyUnresolvedReferences
from System import Uri
# noinspection PyUnresolvedReferences
import System.Windows
# noinspection PyUnresolvedReferences
import System.Windows.Controls as wpfControls


class ExtensionPackageListData:
    def __init__(self, ext_pkg):
        """

        Args:
            ext_pkg (pyrevit.plugins.extpackages.ExtensionPackage):
        """

        self.ext_pkg = ext_pkg
        self.Type = 'Unknown'

        if ext_pkg.type == extpackages.ExtensionTypes.LIB_EXTENSION:
            self.Type = 'IronPython Library'
        elif ext_pkg.type == extpackages.ExtensionTypes.UI_EXTENSION:
            self.Type = 'Revit UI Tools'

        self.Name = ext_pkg.name
        self.Desciption = ext_pkg.description
        self.Author = ext_pkg.author

        self.GitURL = ext_pkg.url
        self.URL = ext_pkg.website

        self.Installed = 'Yes' if ext_pkg.is_installed else 'No'
        self.Status = 'Enabled' if not self.config.disabled else 'Disabled'


    @property
    def config(self):
        try:
            return user_config.get_section(self.ext_pkg.ext_dirname)
        except:
            cfg_section = user_config.add_section(self.ext_pkg.ext_dirname)
            self.config.disabled = False
            self.config.private_repo = False
            self.config.username = self.config.password = ''
            return cfg_section


class InstallPackageMenuItem(wpfControls.MenuItem):
    install_path = ''


class ExtensionsWindow(WPFWindow):
    def __init__(self, xaml_file_name):
        WPFWindow.__init__(self, xaml_file_name)
        self._setup_ext_dirs_ui(user_config.get_ext_root_dirs())
        self._setup_ext_pkg_ui(extpackages.get_ext_packages())

    def _setup_ext_dirs_ui(self, ext_dirs_list):
        for ext_dir in ext_dirs_list:
            ext_dir_install_menu_item = InstallPackageMenuItem()
            ext_dir_install_menu_item.install_path = ext_dir
            ext_dir_install_menu_item.Header = 'Install to:  {}'.format(ext_dir)
            ext_dir_install_menu_item.Click += self.install_ext_pkg
            self.ext_install_b.ContextMenu.AddChild(ext_dir_install_menu_item)

    def _setup_ext_pkg_ui(self, ext_pkgs_list):
        cur_exts_list = []
        for plugin_ext in ext_pkgs_list:
            cur_exts_list.append(ExtensionPackageListData(plugin_ext))

        self.extpkgs_lb.ItemsSource = cur_exts_list
        self.extpkgs_lb.SelectedIndex = 0

    def _update_ext_info_panel(self, ext_pkg_data):
        # Update the name
        self.ext_name_l.Content = ext_pkg_data.Name
        self.ext_desc_l.Text = '{}  '.format(ext_pkg_data.Desciption)
        # Update the description and web link
        if ext_pkg_data.URL:
            self.ext_gitlink_t.Text = '({})'.format(ext_pkg_data.URL)
            self.ext_gitlink_hl.NavigateUri = Uri(ext_pkg_data.URL)

        # Update Installed folder info
        if ext_pkg_data.ext_pkg.is_installed:
            self.show_element(self.ext_installed_l)
            self.ext_installed_l.Content = 'Installed under:\n{}'.format(ext_pkg_data.ext_pkg.is_installed)
        else:
            self.hide_element(self.ext_installed_l)

    def _update_ext_action_buttons(self, ext_pkg_data):
        if ext_pkg_data.ext_pkg.is_installed:
            self.ext_install_b.IsEnabled = False

            self.ext_toggle_b.IsEnabled = True
            if ext_pkg_data.config.disabled:
                self.ext_toggle_b.Content = 'Enable Package'
            else:
                self.ext_toggle_b.Content = 'Disable Package'

            self.ext_remove_b.IsEnabled = True
        else:
            self.ext_install_b.IsEnabled = True
            self.ext_toggle_b.IsEnabled = False
            self.ext_remove_b.IsEnabled = False

    def _update_ext_settings_panel(self, ext_pkg_data):
        try:
            self.privaterepo_cb.IsChecked = ext_pkg_data.config.private_repo
            self.privaterepo_cb.UpdateLayout()
            self.repousername_tb.Text = ext_pkg_data.config.username
            self.repopassword_tb.Text = ext_pkg_data.config.password
        except:
            self.privaterepo_cb.IsChecked = False
            self.repopassword_tb.Text = self.repousername_tb.Text = ''

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def update_ext_info(self, sender, args):
        selected_ext = self.extpkgs_lb.SelectedItem
        if selected_ext:
            self._update_ext_info_panel(selected_ext)
            self._update_ext_action_buttons(selected_ext)
            self._update_ext_settings_panel(selected_ext)

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def handle_url_click(self, sender, args):
        open_url(self.ext_gitlink_hl.NavigateUri.AbsoluteUri)

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def handle_private_repo(self, sender, args):
        if self.privaterepo_cb.IsChecked:
            self.accountcreds_dp.IsEnabled = True
        else:
            self.accountcreds_dp.IsEnabled = False

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def handle_install_button_popup(self, sender, args):
        sender.ContextMenu.IsEnabled = True
        sender.ContextMenu.PlacementTarget = sender
        sender.ContextMenu.Placement = System.Windows.Controls.Primitives.PlacementMode.Bottom
        sender.ContextMenu.IsOpen = True

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def save_pkg_settings(self, sender, args):
        ext_pkg_data = self.extpkgs_lb.SelectedItem
        try:
            ext_pkg_data.config.private_repo = self.privaterepo_cb.IsChecked
            ext_pkg_data.config.username = self.repousername_tb.Text
            ext_pkg_data.config.password = self.repopassword_tb.Text
            user_config.save_changes()
            self.Close()
        except Exception as pkg_sett_save_err:
            logger.error('Error saving extension package settings. | {}'.format(pkg_sett_save_err))

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def install_ext_pkg(self, sender, args):
        print('Work in progress.\nPackage will be cloned to:\n{}'.format(sender.install_path))
        self.Close()

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def toggle_ext_pkg(self, sender, args):
        ext_pkg_data = self.extpkgs_lb.SelectedItem
        ext_pkg_data.config.disabled = not ext_pkg_data.config.disabled
        user_config.save_changes()
        self.Close()

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def remove_ext_pkg(self, sender, args):
        print('Work in progress.\nPackage will be removed.')
        self.Close()


def open_ext_dir_in_explorer(ext_dirs_list):
    for ext_dir in ext_dirs_list:
        open_folder_in_explorer(ext_dir)


if __name__ == '__main__':
    # noinspection PyUnresolvedReferences
    if __shiftclick__:
        open_ext_dir_in_explorer(user_config.get_ext_root_dirs())
    else:
        ExtensionsWindow('ExtensionsWindow.xaml').ShowDialog()
