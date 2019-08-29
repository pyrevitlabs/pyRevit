"""Add or remove pyRevit extensions."""
#pylint: disable=E0401,W0703,W0613,C0103,C0111
import re

from pyrevit import framework
from pyrevit import coreutils
from pyrevit import script
from pyrevit import forms
from pyrevit import extensions as exts
import pyrevit.extensions.extpackages as extpkgs

from pyrevit.userconfig import user_config

import pyrevitcore_globals


__context__ = 'zero-doc'


logger = script.get_logger()


class ExtensionPackageListItem:
    """Extension object that is used in Extensions list ui.

    Attributes:
        Type (str): Type of extension, Library or UI Tools
        Builtin (str): It package is builtin
        Name (str): Package name
        Desciption (str): Package description
        Author (str): Package author
        GitURL (str): Package git repository url
        URL (str): Package website url, optional
        Installed (str): Package is installed, Yes/No
        Status (str): Package is Enabled/Disabled. '--' if not installed
    """

    def __init__(self, extension_package):
        """Initializing the Extension package list item.

        Args:
            extension_package (pyrevit.extensions.extpackages.ExtensionPackage):
        """

        # ref to the pkg object received
        self.ext_pkg = extension_package
        # setting up pretty type name that shows up on the list
        self.Type = 'Unknown'
        if self.ext_pkg.type == \
                exts.ExtensionTypes.LIB_EXTENSION:
            self.Type = 'IronPython Library'
        elif self.ext_pkg.type == \
                exts.ExtensionTypes.UI_EXTENSION:
            self.Type = 'Revit UI Tools'
        elif self.ext_pkg.type == \
                exts.ExtensionTypes.RUN_EXTENSION:
            self.Type = 'CLI Run Commands'

        # setting up other list data
        self.Builtin = self.ext_pkg.builtin
        self.RocketMode = self.ext_pkg.rocket_mode_compatible
        self.Name = self.ext_pkg.name
        self.Desciption = self.ext_pkg.description
        self.Author = self.ext_pkg.author
        self.AuthorProfile = self.ext_pkg.author_profile

        self.GitURL = self.ext_pkg.url
        self.URL = self.ext_pkg.website

        self.Installed = 'Yes' if self.ext_pkg.is_installed else 'No'

        # setting the disabled/enabled pretty name
        if self.ext_pkg.is_installed:
            self.Status = 'Enabled' if not self.ext_pkg.config.disabled \
                                    else 'Disabled'
            if self.ext_pkg.version:
                self.Version = self.ext_pkg.version[:7]
        else:
            self.Status = self.Version = '--'

    def searchable_values(self):
        return ' '.join([self.Type, self.Name, self.Desciption,
                         self.Author, self.Status])


class InstallPackageMenuItem(framework.Controls.MenuItem):
    """Context menu item for package installation destinations

    Instances of this class will be set to the possible directory paths
    that are appropriate to install extensions in. This includes pyRevit
    default extension folder and all other extension folders set by the
    user. When installing an extension, user can select the destination
    from the destinations menu which contains instances of this class.

    Attributes:
        InstallPackageMenuItem.install_path (str): Destination address

    """

    install_path = ''


class ExtensionsWindow(forms.WPFWindow):
    """Extension window managing installation and removal of extensions
    """

    def __init__(self, xaml_file_name):
        forms.WPFWindow.__init__(self, xaml_file_name)
        self._setup_ext_dirs_ui(user_config.get_thirdparty_ext_root_dirs())
        self._setup_ext_pkg_ui(extpkgs.get_ext_packages())

    @property
    def selected_pkg(self):
        """
        Returns the currently selected ExtensionPackageListItem in
        the extension packages list

        Returns:
            ExtensionPackageListItem:
        """
        if len(list(self.extpkgs_lb.SelectedItems)) == 1:
            return self.extpkgs_lb.SelectedItem

    @property
    def selected_pkgs(self):
        """
        Returns all the currently selected ExtensionPackageListItem in
        the extension packages list

        Returns:
            list[ExtensionPackageListItem]:
        """
        return self.extpkgs_lb.SelectedItems

    def _setup_ext_dirs_ui(self, ext_dirs_list):
        """Creates the installation destination context menu. Creates a menu
        item for each directory address provided in ext_dirs_list

        Args:
            ext_dirs_list (list): List of destination directories

        """

        #pylint: disable=E1101,W0201
        for ext_dir in ext_dirs_list:
            ext_dir_install_menu_item = InstallPackageMenuItem()
            ext_dir_install_menu_item.install_path = ext_dir
            ext_dir_install_menu_item.Header = \
                'Install to:  {}'.format(ext_dir)
            ext_dir_install_menu_item.Click += self.install_ext_pkg
            self.ext_install_b.ContextMenu.AddChild(ext_dir_install_menu_item)

    def _setup_ext_pkg_ui(self, ext_pkgs_list):
        """Creates a list of initialized ExtensionPackageListItem objects,
        one for each extension package object in ext_pkgs_list

        Args:
            ext_pkgs_list (list): List of extension packages

        """

        self._exts_list = []
        for plugin_ext in ext_pkgs_list:
            self._exts_list.append(ExtensionPackageListItem(plugin_ext))

        self.extpkgs_lb.ItemsSource = \
            sorted(self._exts_list, key=lambda x: x.Builtin, reverse=True)
        self.extpkgs_lb.SelectedIndex = 0

    def _update_ext_info_panel(self, ext_pkg_item):
        """Updated the extension information panel based on the info
        provided by the ext_pkg_item

        Args:
            ext_pkg_item: Extension package to display info for

        """

        # Update the name
        self.ext_name_l.Content = ext_pkg_item.Name
        self.ext_desc_l.Text = '{}  '.format(ext_pkg_item.Desciption)

        # Update the description and web link
        if ext_pkg_item.URL:
            self.ext_gitlink_t.Text = '({})'.format(ext_pkg_item.URL)
            self.ext_gitlink_hl.NavigateUri = framework.Uri(ext_pkg_item.URL)
        else:
            self.ext_gitlink_t.Text = ''

        # Update the author and profile link
        if ext_pkg_item.Author:
            self.ext_author_t.Text = ext_pkg_item.Author
            self.ext_author_nolink_t.Text = ext_pkg_item.Author
            if ext_pkg_item.AuthorProfile:
                self.ext_authorlink_hl.NavigateUri = \
                    framework.Uri(ext_pkg_item.AuthorProfile)
                self.show_element(self.ext_author_t)
                self.hide_element(self.ext_author_nolink_t)
            else:
                self.hide_element(self.ext_author_t)
                self.show_element(self.ext_author_nolink_t)
        else:
            self.ext_author_t.Text = ''

        # Update the repo link
        if ext_pkg_item.GitURL:
            self.ext_repolink_t.Text = ext_pkg_item.GitURL
            self.ext_repolink_hl.NavigateUri = \
                framework.Uri(ext_pkg_item.GitURL)
        else:
            self.ext_repolink_t.Text = ''

        # Update Installed folder info
        if ext_pkg_item.ext_pkg.is_installed:
            self.show_element(self.ext_installed_l)
            self.ext_installed_l.Content = \
                'Installed under:\n{}' \
                .format(ext_pkg_item.ext_pkg.is_installed)
        else:
            self.hide_element(self.ext_installed_l)

        # Update dependencies
        if ext_pkg_item.ext_pkg.dependencies:
            self.show_element(self.ext_dependencies_l)
            self.ext_dependencies_l.Content = \
                'Dependencies:\n' + \
                ', '.join(ext_pkg_item.ext_pkg.dependencies)
        else:
            self.hide_element(self.ext_dependencies_l)

    def _update_toggle_button(self, enable=True, multiple=False):
        self.show_element(self.ext_toggle_b)
        if enable:
            self.ext_toggle_b.Content = \
                self.ext_toggle_b.Content.replace('Dis', 'En')
        else:
            self.ext_toggle_b.Content = \
                self.ext_toggle_b.Content.replace('En', 'Dis')

        if multiple:
            self.ext_toggle_b.Content = \
                self.ext_toggle_b.Content = \
                    re.sub("Extensions*",
                           "Extensions",
                           self.ext_toggle_b.Content)
        else:
            self.ext_toggle_b.Content = \
                self.ext_toggle_b.Content.replace('Extensions', 'Extension')

    def _update_ext_action_buttons(self, ext_pkg_items):
        """Updates the status of actions buttons depending on the status of
        the provided ext_pkg_item. e.g. disable the Install button if the
        package is already installed.

        Args:
            ext_pkg_items: Extension packages to update the action buttons
        """
        if len(ext_pkg_items) == 1:
            ext_pkg_item = ext_pkg_items[0]
            if ext_pkg_item.ext_pkg.is_installed:
                # Action Button: Install
                self.hide_element(self.ext_install_b)

                # Action Button: Remove
                if ext_pkg_item.ext_pkg.builtin:
                    self.hide_element(self.ext_remove_b)
                else:
                    self.show_element(self.ext_remove_b)

                # Action Button: Toggle (Enable / Disable)
                if ext_pkg_item.ext_pkg.is_cli_ext:
                    self.hide_element(self.ext_toggle_b)
                else:
                    self._update_toggle_button(
                        enable=ext_pkg_item.ext_pkg.config.disabled
                    )
            else:
                self.show_element(self.ext_install_b)
                self.hide_element(self.ext_toggle_b, self.ext_remove_b)
        elif len(ext_pkg_items) > 1:
            self.hide_element(self.ext_update_b)
            self.hide_element(self.ext_install_b)
            self.hide_element(self.ext_remove_b)
            # hide the button if includes any cli extensions
            if any([x.ext_pkg.is_cli_ext for x in ext_pkg_items]):
                self.hide_element(self.ext_toggle_b)
            # hide the button if any ext is not installed
            elif any([not x.ext_pkg.is_installed for x in ext_pkg_items]):
                self.hide_element(self.ext_toggle_b)
            else:
                all_disabled = \
                    [x.ext_pkg.config.disabled for x in ext_pkg_items]
                if all(all_disabled):
                    self._update_toggle_button(enable=True, multiple=True)
                    return

                all_enabled = \
                    [not x.ext_pkg.config.disabled for x in ext_pkg_items]
                if all(all_enabled):
                    self._update_toggle_button(enable=False, multiple=True)
                    return
                # hide the button if mixed enabled and disabled
                self.hide_element(self.ext_toggle_b)

    def _update_ext_settings_panel(self, ext_pkg_item):
        """Updates the package settings panel based on the provided
        package in ext_pkg_item

        Args:
            ext_pkg_item: Extension package to update the settings ui

        """

        if ext_pkg_item.Builtin:
            self.hide_element(self.extCredentials)
            self.hide_element(self.ext_update_b)
        else:
            self.show_element(self.extCredentials)
            self.show_element(self.ext_update_b)
            try:
                # Is package using a private git repo?
                self.privaterepo_cb.IsChecked = \
                    ext_pkg_item.ext_pkg.config.private_repo
                self.privaterepo_cb.UpdateLayout()

                # Set current username and pass for the private repo
                self.repousername_tb.Text = ext_pkg_item.ext_pkg.config.username
                self.repopassword_tb.Text = ext_pkg_item.ext_pkg.config.password
            except Exception:
                self.privaterepo_cb.IsChecked = False
                self.repopassword_tb.Text = self.repousername_tb.Text = ''

    def _list_options(self, option_filter=None):
        if option_filter:
            option_filter = option_filter.lower()
            self.extpkgs_lb.ItemsSource = \
                [x for x in self._exts_list
                 if option_filter in x.searchable_values().lower()]
        else:
            self.extpkgs_lb.ItemsSource = self._exts_list

    def search_txt_changed(self, sender, args):
        if self.search_tb.Text == '':
            self.hide_element(self.clrsearch_b)
        else:
            self.show_element(self.clrsearch_b)

        self._list_options(option_filter=self.search_tb.Text.lower())

    def clear_search(self, sender, args):
        self.search_tb.Text = ' '
        self.search_tb.Clear()
        self.extpkgs_lb.ItemsSource = self._exts_list

    def update_ext_info(self, sender, args):
        """Callback for updating info panel on package selection change
        """
        if self.selected_pkg:
            self.show_element(self.ext_infostack)
            self.show_element(self.ext_infopanel)
            self._update_ext_info_panel(self.selected_pkg)
            self._update_ext_action_buttons([self.selected_pkg])
            self._update_ext_settings_panel(self.selected_pkg)
        elif self.selected_pkgs:
            self.hide_element(self.ext_infostack)
            self.hide_element(self.extCredentials)
            self._update_ext_action_buttons(self.selected_pkgs)
        else:
            self.hide_element(self.ext_infopanel)

    def handle_private_repo(self, sender, args):
        """Callback for updating private status of a package
        """
        if self.privaterepo_cb.IsChecked:
            self.accountcreds_dp.IsEnabled = True
        else:
            self.accountcreds_dp.IsEnabled = False

    def handle_install_button_popup(self, sender, args):
        """Callback for Install package destination context menu

        This callback method will popup a menu with a list of install
        destinations, when the install button is clicked.
        """
        sender.ContextMenu.IsEnabled = True
        sender.ContextMenu.PlacementTarget = sender
        sender.ContextMenu.Placement = \
            framework.Controls.Primitives.PlacementMode.Bottom
        sender.ContextMenu.IsOpen = True

    def save_pkg_settings(self, sender, args):
        """Reads package configuration from UI and saves to package config
        """

        try:
            self.selected_pkg.ext_pkg.config.private_repo = \
                self.privaterepo_cb.IsChecked
            self.selected_pkg.ext_pkg.config.username = \
                self.repousername_tb.Text
            self.selected_pkg.ext_pkg.config.password = \
                self.repopassword_tb.Text
            user_config.save_changes()
            self.Close()
        except Exception as pkg_sett_save_err:
            logger.error('Error saving extension package settings.'
                         ' | {}'.format(pkg_sett_save_err))

    def install_ext_pkg(self, sender, args):
        """Installs the selected extension, then reloads pyRevit
        """

        try:
            extpkgs.install(self.selected_pkg.ext_pkg,
                            sender.install_path)
            self.Close()
            call_reload()
        except Exception as pkg_install_err:
            logger.error('Error installing package.'
                         ' | {}'.format(pkg_install_err))
            self.Close()

    def toggle_ext_pkg(self, sender, args):
        """Enables/Disables the selected exension, then reloads pyRevit
        """
        if self.selected_pkg:
            self.selected_pkg.ext_pkg.toggle_package()
        elif self.selected_pkgs:
            for pkg in self.selected_pkgs:
                pkg.ext_pkg.toggle_package()
        self.Close()
        call_reload()

    def remove_ext_pkg(self, sender, args):
        """Removes the selected exension, then reloads pyRevit
        """

        try:
            extpkgs.remove(self.selected_pkg.ext_pkg)
            self.Close()
            if not self.selected_pkg.ext_pkg.is_cli_ext:
                call_reload()
        except Exception as pkg_remove_err:
            logger.error('Error removing package. | {}'.format(pkg_remove_err))


def open_ext_dirs_in_explorer(ext_dirs_list):
    """Opens each folder provided by ext_dirs_list in window explorer.

    Args:
        ext_dirs_list (list): List of directories to be opened in explorer

    """

    for ext_dir in ext_dirs_list:
        coreutils.open_folder_in_explorer(ext_dir)


def call_reload():
    from pyrevit.loader.sessionmgr import execute_command
    execute_command(pyrevitcore_globals.PYREVIT_CORE_RELOAD_COMMAND_NAME)


# decide if the settings should load or not
def __selfinit__(script_cmp, ui_button_cmp, __rvt__):
    # do not load the tool if user should not config
    if not user_config.user_can_extend:
        return False

# handles tool click in Revit interface:
# if Shift-Click on the tool, opens the extension package destinations in
# windows explorer
# otherwise, will show the Extension manager user interface
if __name__ == '__main__':
    if __shiftclick__:  #pylint: disable=E0602
        open_ext_dirs_in_explorer(user_config.get_ext_root_dirs())
    else:
        ExtensionsWindow('ExtensionsWindow.xaml').show_dialog()
