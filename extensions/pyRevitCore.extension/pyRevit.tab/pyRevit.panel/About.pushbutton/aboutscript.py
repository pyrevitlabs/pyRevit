# -*- coding: utf-8 -*-
import sys

import scriptutils
from scriptutils.userinput import WPFWindow
from pyrevit.versionmgr import get_pyrevit_version, get_pyrevit_repo


__context__ = 'zerodoc'

__doc__ = 'About pyrevit. Opens the pyrevit blog website. You can find ' \
          'detailed information on how pyrevit works, updates about the' \
          'new tools and changes, and a lot of other information there.'


class AboutWindow(WPFWindow):
    def __init__(self, xaml_file_name):
        WPFWindow.__init__(self, xaml_file_name)

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
            pyrvt_repo = get_pyrevit_repo()
            pyrvt_ver = get_pyrevit_version()
            self.version_info.Text = ' v{}' \
                                     .format(pyrvt_ver.get_formatted())
            if pyrvt_repo.branch != 'master':
                self.branch_info.Text = ' ({})'.format(pyrvt_repo.branch)
        except:
            self.version_info.Text = ''

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def opengithubrepopage(self, sender, args):
        scriptutils.open_url('https://github.com/eirannejad/pyRevit')

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def opengithubcommits(self, sender, args):
        scriptutils.open_url('https://github.com/eirannejad/pyRevit/commits/master')

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def openrevisionhistory(self, sender, args):
        scriptutils.open_url('http://eirannejad.github.io/pyRevit/releasenotes/')

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def opencredits(self, sender, args):
        scriptutils.open_url('http://eirannejad.github.io/pyRevit/credits/')

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def openkeybaseprofile(self, sender, args):
        scriptutils.open_url('https://keybase.io/ein')

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def handleclick(self, sender, args):
        self.Close()

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def onactivated(self, sender, args):
        pass
        # pyrvt_repo = get_pyrevit_repo()
        # if has_pending_updates(pyrvt_repo):
        #     hist_div = compare_branch_heads(pyrvt_repo)
        #     self.version_info.Text = '{} {}'
        #                              .format(self.version_info.Text,
        #                                      hist_div.BehindBy)


AboutWindow('AboutWindow.xaml').ShowDialog()
