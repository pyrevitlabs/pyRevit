# -*- coding: utf-8 -*-
import sys

from scriptutils import open_url
from scriptutils.userinput import WPFWindow
from pyrevit.coreutils.git import compare_branch_heads
from pyrevit.versionmgr import PYREVIT_VERSION, PYREVIT_REPO
from pyrevit.versionmgr.updater import get_pyrevit_repo, has_pending_updates


__doc__ = 'About pyrevit. Opens the pyrevit blog website. You can find detailed information on how pyrevit works, ' \
          'updates about the new tools and changes, and a lot of other information there.'


class AboutWindow(WPFWindow):
    def __init__(self, xaml_file_name):
        WPFWindow.__init__(self, xaml_file_name)

        self.set_image_source('image_credits', 'credits.png')
        self.set_image_source('pyrevit_logo', 'pyRevitlogo.png')
        self.set_image_source('keybase_profile', 'keybase.png')

        try:
            self.version_info.Text = 'v{}'.format(PYREVIT_VERSION.get_formatted())
            if PYREVIT_REPO.branch != 'master':
                self.branch_info.Text = ' ({})'.format(PYREVIT_REPO.branch)
        except:
            self.version_info.Text = ''
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

    # noinspection PyUnusedLocal
    # noinspection PyMethodMayBeStatic
    def onactivated(self, sender, args):
        pass
        # pyrvt_repo = get_pyrevit_repo()
        # if has_pending_updates(pyrvt_repo):
        #     hist_div = compare_branch_heads(pyrvt_repo)
        #     self.version_info.Text = '{} {}'.format(self.version_info.Text, hist_div.BehindBy)


if __name__ == '__main__':
    AboutWindow('AboutWindow.xaml').ShowDialog()
