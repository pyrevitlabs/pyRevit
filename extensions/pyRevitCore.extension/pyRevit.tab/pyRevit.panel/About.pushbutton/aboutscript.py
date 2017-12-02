# -*- coding: utf-8 -*-
import sys

from pyrevit import coreutils
from pyrevit import versionmgr
from pyrevit.versionmgr import urls
from pyrevit.versionmgr import about
from pyrevit import forms
from pyrevit import script


__context__ = 'zerodoc'

__doc__ = 'About pyrevit. Opens the pyrevit blog website. You can find ' \
          'detailed information on how pyrevit works, updates about the' \
          'new tools and changes, and a lot of other information there.'


class AboutWindow(forms.WPFWindow):
    def __init__(self, xaml_file_name):
        forms.WPFWindow.__init__(self, xaml_file_name)

        pyrvtabout = about.get_pyrevit_about()

        try:
            pyrvt_repo = versionmgr.get_pyrevit_repo()
            pyrvt_ver = versionmgr.get_pyrevit_version()
            nice_version = ' v{}'.format(pyrvt_ver.get_formatted())
            short_version = \
                ' v{}'.format(pyrvt_ver.get_formatted(nopatch=True))
            branch_info = '{} branch'.format(pyrvt_repo.branch)
        except Exception:
            nice_version = short_version = branch_info = ''

        rocketchar = u'\U0001F680' if sys.version_info.micro > 3 else ''
        rocketmodetext = 'Rocket-mode {}'\
                         .format(u'enabled ' + rocketchar if __cachedengine__
                                 else 'disabled')

        self.short_version_info.Text = short_version
        self.pyrevit_subtitle.Text = pyrvtabout.subtitle
        self.pyrevit_subtitle.Text += '\n {} | {}'.format(nice_version,
                                                          branch_info)
        self.pyrevit_subtitle.Text += '\nRunning on IronPython {}.{}.{}'\
                                      .format(sys.version_info.major,
                                              sys.version_info.minor,
                                              sys.version_info.micro)
        self.pyrevit_subtitle.Text += '\n{}'.format(rocketmodetext)

        self.madein_tb.Text = pyrvtabout.madein
        self.copyright_tb.Text = pyrvtabout.copyright

    def opencredits(self, sender, args):
        script.open_url(urls.credits)

    def opendocs(self, sender, args):
        script.open_url(urls.docs)

    def openblog(self, sender, args):
        script.open_url(urls.blog)

    def opengithubrepopage(self, sender, args):
        script.open_url(urls.github)

    def openyoutubechannel(self, sender, args):
        script.open_url(urls.youtube)

    def opensupportpage(self, sender, args):
        script.open_url(urls.patron)

    def opengithubcommits(self, sender, args):
        script.open_url(urls.githubmastercommits)

    def openreleasenotes(self, sender, args):
        script.open_url(urls.releasenotes)

    def openkeybaseprofile(self, sender, args):
        script.open_url(urls.profile_ein)

    def handleclick(self, sender, args):
        self.Close()


AboutWindow('AboutWindow.xaml').show_dialog()
