# -*- coding: utf-8 -*-
import sys

from pyrevit import coreutils
from pyrevit import versionmgr
from pyrevit import forms


__context__ = 'zerodoc'

__doc__ = 'About pyrevit. Opens the pyrevit blog website. You can find ' \
          'detailed information on how pyrevit works, updates about the' \
          'new tools and changes, and a lot of other information there.'


class AboutWindow(forms.WPFWindow):
    def __init__(self, xaml_file_name):
        forms.WPFWindow.__init__(self, xaml_file_name)

        self.set_image_source('image_credits', 'credits.png')
        self.set_image_source('keybase_profile', 'keybase.png')
        self.pyrevit_subtitle.Text += '\nRunning on IronPython {}.{}.{}' \
                                      .format(sys.version_info.major,
                                              sys.version_info.minor,
                                              sys.version_info.micro)

        if __cachedengine__:
            self.set_image_source('pyrevit_logo', 'pyRevitrocketlogo.png')
            self.pyrevit_subtitle.Text += '\nRocket mode enabled.'
        else:
            self.set_image_source('pyrevit_logo', 'pyRevitlogo.png')

        try:
            pyrvt_repo = versionmgr.get_pyrevit_repo()
            pyrvt_ver = versionmgr.get_pyrevit_version()
            self.version_info.Text = ' v{}' \
                                     .format(pyrvt_ver.get_formatted())
            if pyrvt_repo.branch != 'master':
                self.branch_info.Text = ' ({})'.format(pyrvt_repo.branch)
        except:
            self.version_info.Text = ''

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def opengithubrepopage(self, sender, args):
        coreutils.open_url('https://github.com/eirannejad/pyRevit')

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def opengithubcommits(self, sender, args):
        coreutils.open_url('https://github.com/eirannejad/pyRevit/commits/master')

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def openrevisionhistory(self, sender, args):
        coreutils.open_url('http://eirannejad.github.io/pyRevit/releasenotes/')

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def opencredits(self, sender, args):
        coreutils.open_url('http://eirannejad.github.io/pyRevit/credits/')

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def openkeybaseprofile(self, sender, args):
        coreutils.open_url('https://keybase.io/ein')

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def handleclick(self, sender, args):
        self.Close()


AboutWindow('AboutWindow.xaml').show_dialog()
