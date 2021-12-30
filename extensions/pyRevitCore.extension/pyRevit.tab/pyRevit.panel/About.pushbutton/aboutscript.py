# -*- coding: utf-8 -*-
#pylint: disable=E0401,E0602,W0703,W0613,C0103
import sys

from pyrevit import versionmgr
from pyrevit.versionmgr import urls
from pyrevit.versionmgr import about
from pyrevit import forms
from pyrevit import script
from pyrevit.userconfig import user_config


logger = script.get_logger()


class AboutWindow(forms.WPFWindow):
    def __init__(self, xaml_file_name):
        forms.WPFWindow.__init__(self, xaml_file_name)

        pyrvtabout = about.get_pyrevit_about()

        pyrvt_ver = versionmgr.get_pyrevit_version()
        nice_version = 'v{}'.format(pyrvt_ver.get_formatted())
        short_version = \
            ' v{}'.format(pyrvt_ver.get_formatted(strict=True))

        self.branch_name = self.deployname = None
        # check to see if git repo is valid
        try:
            pyrvt_repo = versionmgr.get_pyrevit_repo()
            self.branch_name = pyrvt_repo.branch
            self.show_element(self.git_commit)
            self.show_element(self.git_branch)
        except Exception as getbranch_ex:
            logger.debug('Error getting branch: %s', getbranch_ex)
            # other wise try to get deployment name
            attachment = user_config.get_current_attachment()
            if attachment:
                try:
                    self.deployname = attachment.Clone.Deployment.Name
                    self.show_element(self.repo_deploy)
                except Exception as getdepl_ex:
                    logger.debug('Error getting depoyment: %s', getdepl_ex)

        # get cli version
        pyrvt_cli_version = 'v' + versionmgr.get_pyrevit_cli_version()
        self.show_element(self.cli_info)
        self.cliversion.Text = pyrvt_cli_version

        self.short_version_info.Text = short_version
        self.pyrevit_subtitle.Text = pyrvtabout.subtitle
        self.version.Text = nice_version
        self.pyrevit_branch.Text = self.branch_name
        self.pyrevit_deploy.Text = '{} deployment'.format(self.deployname)
        cpyver = user_config.get_active_cpython_engine()
        if cpyver:
            self.pyrevit_engine.Text = \
                'Running on IronPython {} (cpython {})'\
                    .format(sys.version.split('(')[0].strip(),
                            '.'.join(list(str(cpyver.Version))))

        rocketmodetext = \
            'Rocket-mode {}' \
            .format('enabled' if __cachedengine__ else 'disabled')
        self.pyrevit_rmode.Text = rocketmodetext
        if not __cachedengine__:
            self.hide_element(self.rmode_icon)

        self.madein_tb.Text = 'in {}'.format(pyrvtabout.madein)
        self.copyright_tb.Text = pyrvtabout.copyright

    def opencredits(self, sender, args):
        script.open_url(urls.PYREVIT_CREDITS)

    def openwiki(self, sender, args):
        script.open_url(urls.PYREVIT_WIKI)

    def opentwitter(self, sender, args):
        script.open_url(urls.PYREVIT_TWITTER)

    def openblog(self, sender, args):
        script.open_url(urls.PYREVIT_BLOG)

    def opengithubrepopage(self, sender, args):
        script.open_url(urls.PYREVIT_GITHUB)

    def openyoutubechannel(self, sender, args):
        script.open_url(urls.PYREVIT_YOUTUBE)

    def opensupportpage(self, sender, args):
        script.open_url(urls.PYREVIT_SUPPORT)

    def opengithubcommits(self, sender, args):
        if self.branch_name:
            commits_url = \
                urls.PYREVIT_GITHUBBRANCH_COMMIT.format(branch=self.branch_name)
            script.open_url(commits_url)

    def opengithubbranch(self, sender, args):
        if self.branch_name:
            branch_url = \
                urls.PYREVIT_GITHUBBRANCH.format(branch=self.branch_name)
            script.open_url(branch_url)

    def openreleasenotes(self, sender, args):
        script.open_url(urls.PYREVIT_RELEASENOTES)

    def openkeybaseprofile(self, sender, args):
        script.open_url(urls.PROFILE_EIN)

    def openlicensepage(self, sender, args):
        script.open_url(urls.PYREVIT_LICENSE)

    def handleclick(self, sender, args):
        self.Close()


AboutWindow('AboutWindow.xaml').show_dialog()
