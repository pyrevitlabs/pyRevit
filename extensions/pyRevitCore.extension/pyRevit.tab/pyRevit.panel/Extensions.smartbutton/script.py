"""Add or remove pyRevit extensions."""

# pylint: disable=E0401,W0703,W0613,C0103,C0111
import re

from pyrevit import framework, os
from pyrevit import coreutils
from pyrevit import script
from pyrevit import forms
from pyrevit import EXEC_PARAMS
from pyrevit import extensions as exts
import pyrevit.extensions.extpackages as extpkgs

from pyrevit.userconfig import user_config

import pyrevitcore_globals


logger = script.get_logger()


def _repo_name_from_git_url(git_url):
    """Derive repo/folder name from a Git URL (e.g. .../owner/repo.git -> repo)."""
    if not git_url:
        return ""
    # Strip .git suffix
    url = git_url.rstrip("/")
    if url.lower().endswith(".git"):
        url = url[:-4]
    # Last path segment: after last / or, for git@host:path, after last /
    if "/" in url:
        url = url.rsplit("/", 1)[-1]
    elif url.startswith("git@"):
        # git@host:owner/repo -> owner/repo -> repo
        if ":" in url:
            url = url.split(":", 1)[1]
        if "/" in url:
            url = url.rsplit("/", 1)[-1]
    return url.strip() or ""


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

    def __init__(self, locale, extension_package):
        """Initializing the Extension package list item.

        Args:
            locale (locale resources)
            extension_package (pyrevit.extensions.extpackages.ExtensionPackage):
        """

        self.locale = locale
        # ref to the pkg object received
        self.ext_pkg = extension_package
        # setting up pretty type name that shows up on the list
        self.Type = self.locale.get_locale_string("Extension.TypeUnknown")
        if self.ext_pkg.type == exts.ExtensionTypes.LIB_EXTENSION:
            self.Type = self.locale.get_locale_string("Extension.TypeIronLibrary")
        elif self.ext_pkg.type == exts.ExtensionTypes.UI_EXTENSION:
            self.Type = self.locale.get_locale_string("Extension.TypeUITools")

        # setting up other list data
        self.Builtin = self.ext_pkg.builtin
        self.RocketMode = self.ext_pkg.rocket_mode_compatible
        self.Name = self.ext_pkg.name
        self.Desciption = self.ext_pkg.description
        self.Author = self.ext_pkg.author
        self.AuthorProfile = self.ext_pkg.author_profile

        self.GitURL = self.ext_pkg.url
        self.URL = self.ext_pkg.website

        self.Installed = (
            self.locale.get_locale_string("Extension.Installed")
            if self.ext_pkg.is_installed
            else self.locale.get_locale_string("Extension.NotInstalled")
        )

        # setting the disabled/enabled pretty name
        if self.ext_pkg.is_installed:
            self.Status = (
                self.locale.get_locale_string("Extension.Enabled")
                if not self.ext_pkg.config.disabled
                else self.locale.get_locale_string("Extension.Disabled")
            )

            if self.ext_pkg.version:
                self.Version = self.ext_pkg.version[:7]
        else:
            self.Status = self.Version = "--"

    def searchable_values(self):
        return " ".join(
            [self.Type, self.Name, self.Desciption, self.Author, self.Status]
        )


class ExtensionsWindow(forms.WPFWindow):
    """Extension window managing installation and removal of extensions"""

    def __init__(self, xaml_file_name):
        forms.WPFWindow.__init__(self, xaml_file_name)
        self._setup_ext_pkg_ui(extpkgs.get_ext_packages())
        default_path = user_config.get_thirdparty_ext_root_dirs(include_default=True)[0]
        self.custom_ext_install_path_tb.Text = default_path
        if self.selected_pkg:
            self._update_add_custom_section_for_selection(self.selected_pkg)
        else:
            self._update_add_custom_section_for_new()

        if self.selected_pkg:
            self._update_ext_action_buttons([self.selected_pkg])
        elif self.selected_pkgs:
            self._update_ext_action_buttons(self.selected_pkgs)
        else:
            self.hide_element(self.ext_toggle_b, self.ext_remove_b, self.ext_deselect_b)

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

    def _setup_ext_pkg_ui(self, ext_pkgs_list):
        """Creates a list of initialized ExtensionPackageListItem objects,
        one for each extension package object in ext_pkgs_list

        Args:
            ext_pkgs_list (list): List of extension packages

        """

        self._exts_list = []
        for plugin_ext in ext_pkgs_list:
            self._exts_list.append(ExtensionPackageListItem(self, plugin_ext))

        self.extpkgs_lb.ItemsSource = sorted(
            self._exts_list, key=lambda x: x.Builtin, reverse=True
        )
        self.extpkgs_lb.SelectedIndex = -1

    def _refresh_extension_list(self):
        """Reload extension packages and refresh the grid (e.g. after installing)."""
        ext_pkgs_list = extpkgs.get_ext_packages()
        self._setup_ext_pkg_ui(ext_pkgs_list)
        self._update_add_custom_section_for_new()

    def _update_ext_info_panel(self, ext_pkg_item):
        """Updated the extension information panel based on the info
        provided by the ext_pkg_item

        Args:
            ext_pkg_item: Extension package to display info for

        """

        # Update the name
        self.ext_name_l.Content = ext_pkg_item.Name
        self.ext_desc_l.Text = "{}  ".format(ext_pkg_item.Desciption)

        # Update the description and web link
        if ext_pkg_item.URL:
            self.ext_gitlink_t.Text = "({})".format(ext_pkg_item.URL)
            self.ext_gitlink_hl.NavigateUri = framework.Uri(ext_pkg_item.URL)
        else:
            self.ext_gitlink_t.Text = ""

        # Update the author and profile link
        if ext_pkg_item.Author:
            self.ext_author_t.Text = ext_pkg_item.Author
            self.ext_author_nolink_t.Text = ext_pkg_item.Author
            if ext_pkg_item.AuthorProfile:
                self.ext_authorlink_hl.NavigateUri = framework.Uri(
                    ext_pkg_item.AuthorProfile
                )
                self.show_element(self.ext_author_t)
                self.hide_element(self.ext_author_nolink_t)
            else:
                self.hide_element(self.ext_author_t)
                self.show_element(self.ext_author_nolink_t)
        else:
            self.ext_author_t.Text = ""

        # Update the repo link
        if ext_pkg_item.GitURL:
            self.ext_repolink_t.Text = ext_pkg_item.GitURL
            self.ext_repolink_hl.NavigateUri = framework.Uri(ext_pkg_item.GitURL)
        else:
            self.ext_repolink_t.Text = ""

        # Update install path (own line, like Developed by)
        if ext_pkg_item.ext_pkg.is_installed:
            self.show_element(self.ext_installpath_tb)
            self.ext_installpath_tb.Text = (
                self.get_locale_string("ExtensionInfo.InstallPathLink")
                + ext_pkg_item.ext_pkg.is_installed
            )
        else:
            self.hide_element(self.ext_installpath_tb)

        # Update dependencies
        if ext_pkg_item.ext_pkg.dependencies:
            self.show_element(self.ext_dependencies_l)
            self.ext_dependencies_l.Content = (
                self.get_locale_string("Extension.Dependencies")
                + "\n"
                + ", ".join(ext_pkg_item.ext_pkg.dependencies)
            )
        else:
            self.hide_element(self.ext_dependencies_l)

    def _update_toggle_button(self, enable=True, multiple=False):
        self.show_element(self.ext_toggle_b)
        if enable:
            self.ext_toggle_b.Content = (
                self.get_locale_string("Buttons.ToggleButton.Enable")
            )
        else:
            self.ext_toggle_b.Content = (
                self.get_locale_string("Buttons.ToggleButton.Disable")
            )

        if multiple:
            self.ext_toggle_b.Content = re.sub(
                "Extensions*", "Extensions", self.ext_toggle_b.Content
            )
        else:
            self.ext_toggle_b.Content = self.ext_toggle_b.Content.replace(
                "Extensions", "Extension"
            )

    def _update_ext_action_buttons(self, ext_pkg_items):
        """Updates the extension action button based on ext_pkg_item

        Args:
            ext_pkg_items (list): List of extension packages
        """
        self.show_element(self.ext_deselect_b)

        if len(ext_pkg_items) == 1:
            ext_pkg_item = ext_pkg_items[0]
            if ext_pkg_item.ext_pkg.is_installed:
                # Action Button: Remove
                if ext_pkg_item.ext_pkg.builtin:
                    self.hide_element(self.ext_remove_b)
                else:
                    self.show_element(self.ext_remove_b)

                # Action Button: Toggle (Enable / Disable)
                self._update_toggle_button(enable=ext_pkg_item.ext_pkg.config.disabled)
            else:
                self.hide_element(self.ext_toggle_b, self.ext_remove_b)
        elif len(ext_pkg_items) > 1:
            self.hide_element(self.ext_remove_b)
            # hide the button if includes any cli extensions
            if any([not x.ext_pkg.is_installed for x in ext_pkg_items]):
                self.hide_element(self.ext_toggle_b)
            else:
                all_disabled = [x.ext_pkg.config.disabled for x in ext_pkg_items]
                if all(all_disabled):
                    self._update_toggle_button(enable=True, multiple=True)
                    return

                all_enabled = [not x.ext_pkg.config.disabled for x in ext_pkg_items]
                if all(all_enabled):
                    self._update_toggle_button(enable=False, multiple=True)
                    return
                # hide the button if mixed enabled and disabled
                self.hide_element(self.ext_toggle_b)

    def _list_options(self, option_filter=None):
        if option_filter:
            option_filter = option_filter.lower()
            self.extpkgs_lb.ItemsSource = [
                x
                for x in self._exts_list
                if option_filter in x.searchable_values().lower()
            ]
        else:
            self.extpkgs_lb.ItemsSource = self._exts_list

    def search_txt_changed(self, sender, args):
        if self.search_tb.Text == "":
            self.hide_element(self.clrsearch_b)
        else:
            self.show_element(self.clrsearch_b)

        self._list_options(option_filter=self.search_tb.Text.lower())

    def clear_search(self, sender, args):
        self.search_tb.Clear()
        self.extpkgs_lb.ItemsSource = self._exts_list

    def update_ext_info(self, sender, args):
        """Callback for updating info panel on package selection change"""
        if self.selected_pkg:
            self.show_element(self.ext_infostack)
            self.show_element(self.ext_infopanel)
            self._update_ext_info_panel(self.selected_pkg)
            self._update_ext_action_buttons([self.selected_pkg])
            self._update_add_custom_section_for_selection(self.selected_pkg)
        elif self.selected_pkgs:
            self.hide_element(self.ext_infostack)
            self._update_ext_action_buttons(self.selected_pkgs)
            self._update_add_custom_section_for_new()
        else:
            self.show_element(self.ext_infopanel)
            self.hide_element(self.ext_infostack)
            self.hide_element(self.ext_toggle_b, self.ext_remove_b, self.ext_deselect_b)
            self._update_add_custom_section_for_new()

    def _update_add_custom_section_for_selection(self, ext_pkg_item):
        """Populate Add Custom section from selected extension; disable Pick, show Install only if not installed."""
        self.custom_git_url_tb.Text = ext_pkg_item.GitURL or ""
        if getattr(self, "custom_ext_name_tb", None):
            self.custom_ext_name_tb.Text = ext_pkg_item.Name or ""
        self.custom_git_url_tb.IsReadOnly = True
        if getattr(self, "custom_ext_name_tb", None):
            self.custom_ext_name_tb.IsReadOnly = True
        self.path_custom_ext_b.IsEnabled = False
        if ext_pkg_item.ext_pkg.is_installed:
            self.custom_ext_install_path_tb.Text = ext_pkg_item.ext_pkg.is_installed
        else:
            default_path = user_config.get_thirdparty_ext_root_dirs(include_default=True)[0]
            self.custom_ext_install_path_tb.Text = default_path
        if ext_pkg_item.ext_pkg.is_installed:
            self.hide_element(self.install_custom_ext_b)
        else:
            self.show_element(self.install_custom_ext_b)
            self.install_custom_ext_b.Content = self.get_locale_string("Buttons.InstallExtension")

    def _update_add_custom_section_for_new(self):
        """Reset Add Custom section for adding a new extension; enable Pick, show Add and install."""
        self.custom_git_url_tb.Text = ""
        if getattr(self, "custom_ext_name_tb", None):
            self.custom_ext_name_tb.Text = ""
        self.custom_git_url_tb.IsReadOnly = False
        if getattr(self, "custom_ext_name_tb", None):
            self.custom_ext_name_tb.IsReadOnly = False
        self.path_custom_ext_b.IsEnabled = True
        default_path = user_config.get_thirdparty_ext_root_dirs(include_default=True)[0]
        self.custom_ext_install_path_tb.Text = default_path
        self.show_element(self.install_custom_ext_b)
        self._update_ext_info_from_git_fields()

    def _update_ext_info_from_git_fields(self):
        """Update extension details panel from Git information fields when in add-new mode."""
        if self.custom_git_url_tb.IsReadOnly:
            return
        name = ""
        if getattr(self, "custom_ext_name_tb", None):
            name = self.custom_ext_name_tb.Text.strip()
        url = self.custom_git_url_tb.Text.strip()
        path = self.custom_ext_install_path_tb.Text.strip()
        if name or url or path:
            self.show_element(self.ext_infostack)
            display_name = name or (_repo_name_from_git_url(url) if url else "") or "(enter Git URL)"
            self.ext_name_l.Content = display_name
            self.ext_desc_l.Text = (url + "  ") if url else ""
            if url and (url.startswith("http://") or url.startswith("https://")):
                self.ext_gitlink_t.Text = "(" + url + ")"
                self.ext_gitlink_hl.NavigateUri = framework.Uri(url)
            else:
                self.ext_gitlink_t.Text = ""
            self.ext_author_t.Text = ""
            self.ext_author_nolink_t.Text = ""
            self.ext_repolink_t.Text = ""
            if path:
                self.show_element(self.ext_installpath_tb)
                self.ext_installpath_tb.Text = (
                    self.get_locale_string("ExtensionInfo.InstallPathLink") + path
                )
            else:
                self.hide_element(self.ext_installpath_tb)
            self.hide_element(self.ext_dependencies_l)
        else:
            self.hide_element(self.ext_infostack)

    def git_info_text_changed(self, sender, args):
        """When Git information fields change, update the details panel if in add-new mode."""
        if self.custom_git_url_tb.IsReadOnly:
            return
        self._update_ext_info_from_git_fields()
        self.install_custom_ext_b.Content = self.get_locale_string("AddCustomExtension.AddAndInstall")

    def custom_extension_path(self, sender, args):
        "Picks a folder to install to"
        custom_path = forms.pick_folder(owner=self)
        if custom_path:
            custom_path = os.path.normpath(custom_path)
        self.custom_ext_install_path_tb.Text = custom_path if custom_path else ""
        self._update_ext_info_from_git_fields()

    def install_custom_extension(self, sender, args):
        """Installs a custom extension from a Git URL or the selected catalog extension."""

        try:
            # Catalog install: selected extension from list, not yet installed
            if self.selected_pkg and not self.selected_pkg.ext_pkg.is_installed:
                dest_path = self.custom_ext_install_path_tb.Text
                if not dest_path:
                    ext_dirs = user_config.get_thirdparty_ext_root_dirs(include_default=True)
                    dest_path = ext_dirs[0]
                token = self.custom_token_pb.Password.strip()
                if token:
                    self.selected_pkg.ext_pkg.config.private_repo = True
                    self.selected_pkg.ext_pkg.config.token = token
                extpkgs.install(self.selected_pkg.ext_pkg, dest_path)
                self._refresh_extension_list()
                self.Close()
                call_reload()
                return

            # Add new extension from Git URL
            git_url = self.custom_git_url_tb.Text.strip()
            _name_tb = getattr(self, "custom_ext_name_tb", None)
            ext_name = (_name_tb.Text.strip() if _name_tb else "") or _repo_name_from_git_url(git_url)
            token = self.custom_token_pb.Password.strip()

            # Validation
            if not git_url:
                forms.alert("Please enter a Git URL.", exitscript=False)
                return

            if not ext_name:
                forms.alert("Could not derive extension name from URL. Please enter a Git URL with a repo path (e.g. .../owner/repo.git).", exitscript=False)
                return

            # Check if URL is valid git URL
            if not (
                git_url.startswith("http://")
                or git_url.startswith("https://")
                or git_url.startswith("git@")
            ):
                forms.alert(
                    "Git URL must start with https://, http://, or git@",
                    exitscript=False,
                )
                return

            # Use a clean URL; token is passed via config and used by git_clone
            # (embedding credentials in the URL can cause "too many redirects or
            # authentication replays" with libgit2)
            if git_url.startswith("https://") or git_url.startswith("http://"):
                if "@" in git_url.split("://", 1)[1].split("/")[0]:
                    # Strip existing credentials from URL
                    protocol, rest = git_url.split("://", 1)
                    rest = rest.split("@", 1)[-1]
                    git_url = protocol + "://" + rest

            # Get default extension directory
            dest_path = self.custom_ext_install_path_tb.Text
            if not dest_path:
                ext_dirs = user_config.get_thirdparty_ext_root_dirs(include_default=True)
                dest_path = ext_dirs[0]  # Use the default directory

            logger.info('Installing extension "{}" from {}'.format(ext_name, git_url))
            logger.info("Destination: {}".format(dest_path))

            # Create a temporary extension package object
            from pyrevit.extensions.extpackages import ExtensionPackage

            temp_info = {
                'type': 'temp_type',
                'name': 'temp_name',
                'description': 'temp_desc',
                'url': git_url,
            }

            temp_pkg = ExtensionPackage(temp_info)
            temp_pkg.name = ext_name
            temp_pkg.url = git_url
            temp_pkg.type = exts.ExtensionTypes.UI_EXTENSION

            # If token was provided, store it in config
            if token:
                temp_pkg.config.private_repo = True
                temp_pkg.config.token = token

            extpkgs.install(temp_pkg, dest_path)
            self._refresh_extension_list()

            forms.alert(
                'Extension "{}" installed successfully! \n'
                "Revit will reload to apply changes.".format(ext_name),
                exitscript=False,
            )

            self.Close()
            call_reload()

        except Exception as custom_install_err:
            logger.exception(
                "Error installing custom extension." " | {}".format(custom_install_err)
            )
            forms.alert(
                "Error installing extension: \n{}".format(str(custom_install_err)),
                exitscript=False,
            )

    def deselect_extension(self, sender, args):
        """Clear list selection so the user can return to add-new-extension mode."""
        self.extpkgs_lb.SelectedIndex = -1

    def toggle_ext_pkg(self, sender, args):
        """Enables/Disables the selected extension, then reloads pyRevit"""
        if self.selected_pkg:
            self.selected_pkg.ext_pkg.toggle_package()
        elif self.selected_pkgs:
            for pkg in self.selected_pkgs:
                pkg.ext_pkg.toggle_package()
        self.Close()
        call_reload()

    def remove_ext_pkg(self, sender, args):
        """Removes the selected extension, then reloads pyRevit"""

        try:
            extpkgs.remove(self.selected_pkg.ext_pkg)
            self.Close()
            call_reload()
        except Exception as pkg_remove_err:
            logger.error("Error removing package. | {}".format(pkg_remove_err))
            forms.alert(
                "Error removing extension:\n{}".format(str(pkg_remove_err)),
                exitscript=False,
            )


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
if __name__ == "__main__":
    if EXEC_PARAMS.config_mode:
        open_ext_dirs_in_explorer(user_config.get_ext_root_dirs())
    else:
        ExtensionsWindow("ExtensionsWindow.xaml").show_dialog()
