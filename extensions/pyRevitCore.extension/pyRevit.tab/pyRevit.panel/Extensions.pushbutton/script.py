"""Add or remove pyRevit extensions."""


from pyrevit.coreutils import open_folder_in_explorer
from pyrevit.plugins import extpackages
from pyrevit.userconfig import user_config

from scriptutils import logger
from scriptutils import open_url
from scriptutils.userinput import WPFWindow


class ExtensionPackageData:
    def __init__(self, ext_pkg):
        """

        Args:
            ext_pkg (pyrevit.plugins.extpackages.ExtensionPackage):
        """

        self.Type = 'Unknown'

        if ext_pkg.type == extpackages.ExtensionTypes.LIB_EXTENSION:
            self.Type = 'IronPython Library'
        elif ext_pkg.type == extpackages.ExtensionTypes.UI_EXTENSION:
            self.Type = 'Revit UI Tools'

        self.Name = '\n'.join([ext_pkg.name, ext_pkg.description])
        self.URL = ext_pkg.url
        # fixme self.Version = ext_pkg.version
        self.Version = 'N/I'
        self.Installed = 'Yes' if ext_pkg.is_installed else 'No'


class ExtensionsWindow(WPFWindow):
    def __init__(self, xaml_file_name):
        WPFWindow.__init__(self, xaml_file_name)
        self.extpkgs_lb.ItemsSource = []

        self._setup_ext_dirs_ui(user_config.get_ext_root_dirs())

        for plugin_ext in extpackages.get_ext_packages():
            logger.debug('Adding package to UI: {}'.format(plugin_ext))
            self._add_ext_pkg_ui(ExtensionPackageData(plugin_ext))

    def _setup_ext_dirs_ui(self, ext_dirs_list):
        pass

    def _add_ext_pkg_ui(self, plugin_ext):
        cur_exts_list = self.extpkgs_lb.ItemsSource
        cur_exts_list.append(plugin_ext)
        self.extpkgs_lb.ItemsSource = cur_exts_list

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def install_ext_pkg(self, sender, args):
        pass

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def remove_ext_pkg(self, sender, args):
        pass

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def handle_pkg_dclick(self, sender, args):
        # if args.ClickCount >= 2:
        open_url('https://github.com/eirannejad/pyRevit')


def open_ext_dir_in_explorer(ext_dirs_list):
    for ext_dir in ext_dirs_list:
        open_folder_in_explorer(ext_dir)


if __name__ == '__main__':
    # noinspection PyUnresolvedReferences
    if __shiftclick__:
        open_ext_dir_in_explorer(user_config.get_ext_root_dirs())
    else:
        ExtensionsWindow('ExtensionsWindow.xaml').ShowDialog()