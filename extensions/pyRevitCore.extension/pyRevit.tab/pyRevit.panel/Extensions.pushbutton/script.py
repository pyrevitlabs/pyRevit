"""Add or remove pyRevit extensions."""

from pyrevit.coreutils import open_folder_in_explorer
from pyrevit.loader.sessionmgr import load_session
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


class ExtensionPackageListItem:
    def __init__(self, extension_package):
        """

        Args:
            extension_package (pyrevit.plugins.extpackages.ExtensionPackage):
        """

        self.ext_pkg = extension_package
        self.Type = 'Unknown'

        if self.ext_pkg.type == extpackages.ExtensionTypes.LIB_EXTENSION:
            self.Type = 'IronPython Library'
        elif self.ext_pkg.type == extpackages.ExtensionTypes.UI_EXTENSION:
            self.Type = 'Revit UI Tools'

        self.Name = self.ext_pkg.name
        self.Desciption = self.ext_pkg.description
        self.Author = self.ext_pkg.author

        self.GitURL = self.ext_pkg.url
        self.URL = self.ext_pkg.website

        self.Installed = 'Yes' if self.ext_pkg.is_installed else 'No'
        if self.ext_pkg.is_installed:
            self.Status = 'Enabled' if not self.ext_pkg.config.disabled else 'Disabled'
            if self.ext_pkg.version:
                self.Version = self.ext_pkg.version[:7]
        else:
            self.Status = self.Version = '--'


class InstallPackageMenuItem(wpfControls.MenuItem):
    install_path = ''


class ExtensionsWindow(WPFWindow):
    def __init__(self, xaml_file_name):
        WPFWindow.__init__(self, xaml_file_name)
        self._setup_ext_dirs_ui(user_config.get_ext_root_dirs())
        self._setup_ext_pkg_ui(extpackages.get_ext_packages())

    @property
    def selected_pkg(self):
        """
        Returns the currently selected ExtensionPackageListItem in the extension packages list
        Returns:
            ExtensionPackageListItem:
        """
        return self.extpkgs_lb.SelectedItem

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
            cur_exts_list.append(ExtensionPackageListItem(plugin_ext))

        self.extpkgs_lb.ItemsSource = cur_exts_list
        self.extpkgs_lb.SelectedIndex = 0

    def _update_ext_info_panel(self, ext_pkg_item):
        # Update the name
        self.ext_name_l.Content = ext_pkg_item.Name
        self.ext_desc_l.Text = '{}  '.format(ext_pkg_item.Desciption)

        # Update the description and web link
        if ext_pkg_item.URL:
            self.ext_gitlink_t.Text = '({})'.format(ext_pkg_item.URL)
            self.ext_gitlink_hl.NavigateUri = Uri(ext_pkg_item.URL)

        # Update the author and profile link
        if ext_pkg_item.Author:
            self.ext_author_t.Text = ext_pkg_item.Author
            self.ext_authorlink_hl.NavigateUri = Uri(ext_pkg_item.ext_pkg.author_profile)

        # Update Installed folder info
        if ext_pkg_item.ext_pkg.is_installed:
            self.show_element(self.ext_installed_l)
            self.ext_installed_l.Content = 'Installed under:\n{}'.format(ext_pkg_item.ext_pkg.is_installed)
        else:
            self.hide_element(self.ext_installed_l)

    def _update_ext_action_buttons(self, ext_pkg_item):
        if ext_pkg_item.ext_pkg.is_installed:
            self.hide_element(self.ext_install_b)

            self.show_element(self.ext_toggle_b)
            if ext_pkg_item.ext_pkg.config.disabled:
                self.ext_toggle_b.Content = 'Enable Package'
            else:
                self.ext_toggle_b.Content = 'Disable Package'

            self.show_element(self.ext_remove_b)
        else:
            self.show_element(self.ext_install_b)
            self.hide_element(self.ext_toggle_b, self.ext_remove_b)

    def _update_ext_settings_panel(self, ext_pkg_item):
        try:
            self.privaterepo_cb.IsChecked = ext_pkg_item.ext_pkg.config.private_repo
            self.privaterepo_cb.UpdateLayout()
            self.repousername_tb.Text = ext_pkg_item.ext_pkg.config.username
            self.repopassword_tb.Text = ext_pkg_item.ext_pkg.config.password
        except:
            self.privaterepo_cb.IsChecked = False
            self.repopassword_tb.Text = self.repousername_tb.Text = ''

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def update_ext_info(self, sender, args):
        self._update_ext_info_panel(self.selected_pkg)
        self._update_ext_action_buttons(self.selected_pkg)
        self._update_ext_settings_panel(self.selected_pkg)

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def handle_url_click(self, sender, args):
        open_url(sender.NavigateUri.AbsoluteUri)

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
        try:
            self.selected_pkg.ext_pkg.config.private_repo = self.privaterepo_cb.IsChecked
            self.selected_pkg.ext_pkg.config.username = self.repousername_tb.Text
            self.selected_pkg.ext_pkg.config.password = self.repopassword_tb.Text
            user_config.save_changes()
            self.Close()
        except Exception as pkg_sett_save_err:
            logger.error('Error saving extension package settings. | {}'.format(pkg_sett_save_err))

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def install_ext_pkg(self, sender, args):
        try:
            self.selected_pkg.ext_pkg.install(sender.install_path)
            self.Close()
            load_session()
        except Exception as pkg_install_err:
            logger.error('Error installing package. | {}'.format(pkg_install_err))
            self.Close()

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def toggle_ext_pkg(self, sender, args):
        self.selected_pkg.ext_pkg.config.disabled = not self.selected_pkg.ext_pkg.config.disabled
        user_config.save_changes()
        self.Close()
        load_session()

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def remove_ext_pkg(self, sender, args):
        try:
            self.selected_pkg.ext_pkg.remove()
            self.Close()
            load_session()
        except Exception as pkg_remove_err:
            logger.error('Error removing package. | {}'.format(pkg_remove_err))


def open_ext_dir_in_explorer(ext_dirs_list):
    for ext_dir in ext_dirs_list:
        open_folder_in_explorer(ext_dir)


if __name__ == '__main__':
    # noinspection PyUnresolvedReferences
    if __shiftclick__:
        open_ext_dir_in_explorer(user_config.get_ext_root_dirs())
    else:
        ExtensionsWindow('ExtensionsWindow.xaml').ShowDialog()
