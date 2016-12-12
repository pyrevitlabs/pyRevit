# -*- coding: utf-8 -*-

"""
Copyright (c) 2014-2016 Ehsan Iran-Nejad
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

__doc__ = 'About pyrevit. Opens the pyrevit blog website. You can find detailed information on how pyrevit works, ' \
          'updates about the new tools and changes, and a lot of other information there.'

import os
import sys

import clr
from pyrevit.repo import PYREVIT_VERSION

clr.AddReferenceByPartialName('PresentationCore')
clr.AddReferenceByPartialName("PresentationFramework")
clr.AddReferenceByPartialName('System.Windows.Forms')
clr.AddReferenceByPartialName('WindowsBase')
# noinspection PyUnresolvedReferences
import System.Windows


# fixme: Update about using wpf

class aboutWindow:
    def __init__(self):
        # Create window
        self.my_window = System.Windows.Window()
        self.my_window.WindowStyle = System.Windows.WindowStyle.None
        self.my_window.AllowsTransparency = True
        self.my_window.Background = None
        self.my_window.Title = 'About pyrevit'
        self.my_window.Width = 580
        self.my_window.Height = 315
        self.my_window.ResizeMode = System.Windows.ResizeMode.CanMinimize
        self.my_window.WindowStartupLocation = System.Windows.WindowStartupLocation.CenterScreen
        self.my_window.PreviewKeyDown += self.handle_esc_key
        self.my_window.MouseUp += self.handle_click
        border = System.Windows.Controls.Border()
        border.CornerRadius = System.Windows.CornerRadius(15)
        border.Background = System.Windows.Media.SolidColorBrush(System.Windows.Media.Color.FromArgb(248, 240, 240, 240))
        self.my_window.Content = border

        fontfam = System.Windows.Media.FontFamily('Courier New')

        # Create StackPanel to Layout UI elements
        self.my_stack = System.Windows.Controls.StackPanel()
        self.my_stack.Margin = System.Windows.Thickness(5)
        border.Child = self.my_stack

        self.reponame = System.Windows.Controls.Label()
        self.reponame.Content = 'pyRevit'
        self.reponame.FontFamily = fontfam
        self.reponame.FontSize = 44.0
        self.reponame.Margin = System.Windows.Thickness(30, 20, 30, 0)

        self.versionlabel = System.Windows.Controls.Label()
        tag_line = 'IronPython Library and Scripts for Autodesk Revit'
        sub_title = '{}\nv {}\n'.format(tag_line, PYREVIT_VERSION.get_formatted())
        self.versionlabel.Content = sub_title
        self.versionlabel.FontFamily = fontfam
        self.versionlabel.FontSize = 16.0
        self.versionlabel.Margin = System.Windows.Thickness(30, -10, 30, 0)

        self.ipyversion = System.Windows.Controls.Label()
        running_on = 'Running on IronPython {}.{}.{}'.format(sys.version_info.major,
                                                             sys.version_info.minor,
                                                             sys.version_info.micro)
        self.ipyversion.Content = running_on
        self.ipyversion.FontFamily = fontfam
        self.ipyversion.FontSize = 14.0
        self.ipyversion.Margin = System.Windows.Thickness(30, -10, 30, 0)

        self.my_stack.Children.Add(self.reponame)
        self.my_stack.Children.Add(self.versionlabel)
        self.my_stack.Children.Add(self.ipyversion)

        self.my_button_openwebsite = System.Windows.Controls.Button()
        self.my_button_openwebsite.Content = 'Open pyrevit website'
        self.my_button_openwebsite.Margin = System.Windows.Thickness(30, 10, 30, 0)
        self.my_button_openwebsite.Click += self.openwebsite
        self.my_button_openwebsite.Cursor = System.Windows.Input.Cursors.Hand

        self.my_button_opencredits = System.Windows.Controls.Button()
        self.my_button_opencredits.Content = 'Open Credits webpage'
        self.my_button_opencredits.Margin = System.Windows.Thickness(30, 10, 30, 0)
        self.my_button_opencredits.Click += self.opencredits
        self.my_button_opencredits.Cursor = System.Windows.Input.Cursors.Hand

        self.my_button_openrevisionhistory = System.Windows.Controls.Button()
        self.my_button_openrevisionhistory.Content = 'Open Revision History webpage'
        self.my_button_openrevisionhistory.Margin = System.Windows.Thickness(30, 10, 30, 0)
        self.my_button_openrevisionhistory.Click += self.openrevisionhistory
        self.my_button_openrevisionhistory.Cursor = System.Windows.Input.Cursors.Hand

        self.my_button_opengithubrepopage = System.Windows.Controls.Button()
        self.my_button_opengithubrepopage.Content = 'Open Github Repository for this library'
        self.my_button_opengithubrepopage.Margin = System.Windows.Thickness(30, 10, 30, 0)
        self.my_button_opengithubrepopage.Click += self.opengithubrepopage
        self.my_button_opengithubrepopage.Cursor = System.Windows.Input.Cursors.Hand

        self.my_stack.Children.Add(self.my_button_openwebsite)
        self.my_stack.Children.Add(self.my_button_opencredits)
        self.my_stack.Children.Add(self.my_button_openrevisionhistory)
        self.my_stack.Children.Add(self.my_button_opengithubrepopage)

    # noinspection PyUnusedLocal
    def handle_click(self, sender, args):
        self.my_window.Close()

    # noinspection PyUnusedLocal
    def handle_esc_key(self, sender, args):
        if args.Key == System.Windows.Input.Key.Escape:
            self.my_window.Close()

    # noinspection PyUnusedLocal
    def openwebsite(self, sender, args):
        os.system('start http://eirannejad.github.io/pyRevit/')

    # noinspection PyUnusedLocal
    def opencredits(self, sender, args):
        os.system('start http://eirannejad.github.io/pyRevit/credits/')

    # noinspection PyUnusedLocal
    def openrevisionhistory(self, sender, args):
        os.system('start http://eirannejad.github.io/pyRevit/releasenotes/')

    # noinspection PyUnusedLocal
    def opengithubrepopage(self, sender, args):
        os.system('start https://github.com/eirannejad/pyRevit')

    # noinspection PyUnusedLocal
    def showwindow(self):
        self.my_window.ShowDialog()


aboutWindow().showwindow()
