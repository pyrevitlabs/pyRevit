# -*- coding: utf-8 -*-
import sys

from pyrevit import coreutils
from pyrevit import versionmgr
from pyrevit.versionmgr import urls
from pyrevit.versionmgr import about
from pyrevit.locales import _
from pyrevit import forms
from pyrevit import script


__context__ = 'zerodoc'

__doc__ = _('About pyrevit. Opens the pyrevit blog website. You can find '
            'detailed information on how pyrevit works, updates about the '
            'new tools and changes, and a lot of other information there.')


class AboutWindow(forms.WPFWindow):
    def __init__(self, xaml_file_name):
        forms.WPFWindow.__init__(self, xaml_file_name)

        pyrvtabout = about.get_pyrevit_about()

        try:
            pyrvt_repo = versionmgr.get_pyrevit_repo()
            pyrvt_ver = versionmgr.get_pyrevit_version()
            nice_version = 'v{}'.format(pyrvt_ver.get_formatted())
            short_version = \
                ' v{}'.format(pyrvt_ver.get_formatted(nopatch=True))
            self.branch_name = pyrvt_repo.branch
        except Exception:
            nice_version = short_version = ''
            self.branch_name = None

        self.short_version_info.Text = short_version
        self.pyrevit_subtitle.Text = pyrvtabout.subtitle
        self.pyrevit_version.Text = nice_version
        self.pyrevit_branch.Text = self.branch_name
        self.pyrevit_engine.Text = \
            _('Running on IronPython {}.{}.{}')\
            .format(sys.version_info.major,
                    sys.version_info.minor,
                    sys.version_info.micro)

        rocketmodetext = \
            _('Rocket-mode {}') \
            .format(_('enabled') if __cachedengine__ else _('disabled')) #noqa
        self.pyrevit_rmode.Text = rocketmodetext
        if not __cachedengine__:  #noqa
            self.hide_element(self.rmode_icon)

        self.madein_tb.Text = _('in {}').format(pyrvtabout.madein)
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
        if self.branch_name:
            commits_url = \
                urls.githubbranchcommits.format(branch=self.branch_name)
            script.open_url(commits_url)

    def opengithubbranch(self, sender, args):
        if self.branch_name:
            branch_url = urls.githubbranch.format(branch=self.branch_name)
            script.open_url(branch_url)

    def openreleasenotes(self, sender, args):
        script.open_url(urls.releasenotes)

    def openkeybaseprofile(self, sender, args):
        script.open_url(urls.profile_ein)

    def handleclick(self, sender, args):
        self.Close()


AboutWindow('AboutWindow.xaml').show_dialog()
