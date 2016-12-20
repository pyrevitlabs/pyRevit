# -*- coding: utf-8 -*-

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
import sys

from scriptutils import open_url
from scriptutils.userinput import WPFWindow
from pyrevit.versionmgr import PYREVIT_VERSION


__doc__ = 'About pyrevit. Opens the pyrevit blog website. You can find detailed information on how pyrevit works, ' \
          'updates about the new tools and changes, and a lot of other information there.'


class AboutWindow(WPFWindow):
    def __init__(self, xaml_file_name):
        WPFWindow.__init__(self, xaml_file_name)

        self.set_image_source('image_credits', 'credits.png')
        self.set_image_source('pyrevit_logo', 'pyRevitlogo.png')
        self.set_image_source('keybase_profile', 'keybase.png')

        self.version_info.Text = 'v {}'.format(PYREVIT_VERSION.get_formatted())
        self.pyrevit_subtitle.Text += '\nRunning on IronPython {}.{}.{}'.format(sys.version_info.major,
                                                                                sys.version_info.minor,
                                                                                sys.version_info.micro)

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def opengithubrepopage(self, sender, args):
        open_url('https://github.com/eirannejad/pyRevit')

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def opengithubcommits(self, sender, args):
        open_url('https://github.com/eirannejad/pyRevit/commits/master')

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def openrevisionhistory(self, sender, args):
        open_url('http://eirannejad.github.io/pyRevit/releasenotes/')

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def opencredits(self, sender, args):
        open_url('http://eirannejad.github.io/pyRevit/credits/')

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def openkeybaseprofile(self, sender, args):
        open_url('https://keybase.io/ein')

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def handleclick(self, sender, args):
        self.Close()


if __name__ == '__main__':
    AboutWindow('AboutWindow.xaml').ShowDialog()
