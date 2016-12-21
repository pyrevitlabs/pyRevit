"""
Copyright (c) 2014-2017 Ehsan Iran-Nejad
Python scripts for Autodesk Revit

This file is part of pyRevit repository at https://github.com/eirannejad/pyRevit

pyRevit is a free set of scripts for Autodesk Revit: you can redistribute it and/or modify
it under the terms of the GNU General Public License version 3, as published by
the Free Software Foundation.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

See this link for a copy of the GNU General Public License protecting this package.
https://github.com/eirannejad/pyRevit/blob/master/LICENSE
"""
import os

from pyrevit.userconfig import user_config
from scriptutils import logger, coreutils
from scriptutils.userinput import WPFWindow, pick_folder


__doc__ = 'Shows the preferences window for pyrevit. You can customize how pyrevit loads and set some basic '\
          'parameters here.\n\nShift-Click: Shows config file in explorer.'


class SettingsWindow(WPFWindow):
    def __init__(self, xaml_file_name):
        WPFWindow.__init__(self, xaml_file_name)

        self.checkupdates_cb.IsChecked = user_config.init.checkupdates
        self.verbose_rb.IsChecked = user_config.init.verbose
        self.debug_rb.IsChecked = user_config.init.debug
        self.filelogging_cb.IsChecked = user_config.init.filelogging
        self.compilecsharp_cb.IsChecked = user_config.init.compilecsharp
        self.compilevb_cb.IsChecked = user_config.init.compilevb

        if user_config.init.bincache:
            self.bincache_rb.IsChecked = True
        else:
            self.asciicache_rb.IsChecked = True

        self.extfolders_lb.ItemsSource = user_config.init.userextensions

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

        user_config.init.checkupdates = self.checkupdates_cb.IsChecked
        user_config.init.verbose = self.verbose_rb.IsChecked
        user_config.init.debug = self.debug_rb.IsChecked
        user_config.init.filelogging = self.filelogging_cb.IsChecked
        user_config.init.bincache = self.bincache_rb.IsChecked
        user_config.init.compilecsharp = self.compilecsharp_cb.IsChecked
        user_config.init.compilevb = self.compilevb_cb.IsChecked

        if isinstance(self.extfolders_lb.ItemsSource, list):
            user_config.init.userextensions = self.extfolders_lb.ItemsSource
        else:
            user_config.init.userextensions = []

        user_config.save_changes()
        self.Close()


if __name__ == '__main__':
    if __shiftclick__:
        coreutils.show_file_in_explorer(user_config.config_file)
    else:
        SettingsWindow('SettingsWindow.xaml').ShowDialog()
