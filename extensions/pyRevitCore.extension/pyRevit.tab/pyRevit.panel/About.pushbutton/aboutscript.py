# -*- coding: utf-8 -*-
import sys

from pyrevit import coreutils
from pyrevit import versionmgr
from pyrevit import forms
from pyrevit import script


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
            if pyrvt_repo.branch != 'master' \
                    and not pyrvt_repo.branch.startswith('release/'):
                self.branch_info.Text = ' ({})'.format(pyrvt_repo.branch)
        except Exception:
            self.version_info.Text = ''

    def opengithubrepopage(self, sender, args):
        script.open_url('https://github.com/eirannejad/pyRevit')

    def opengithubcommits(self, sender, args):
        script.open_url(
            'https://github.com/eirannejad/pyRevit/commits/master')

    def openrevisionhistory(self, sender, args):
        script.open_url('http://eirannejad.github.io/pyRevit/releasenotes/')

    def opencredits(self, sender, args):
        script.open_url('http://eirannejad.github.io/pyRevit/credits/')

    def openkeybaseprofile(self, sender, args):
        script.open_url('https://keybase.io/ein')

    def handleclick(self, sender, args):
        self.Close()


AboutWindow('AboutWindow.xaml').show_dialog()
