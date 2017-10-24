import os
import os.path as op

from pyrevit import HOST_APP
from pyrevit import coreutils
from pyrevit import usagelog
from pyrevit import script
from pyrevit import forms
from pyrevit.coreutils import envvars
from pyrevit.userconfig import user_config
from pyrevit.loader.addin import addinfiles


__context__ = 'zerodoc'

__doc__ = 'Shows the preferences window for pyrevit. You can customize how ' \
          'pyrevit loads and set some basic parameters here.' \
          '\n\nShift-Click: Shows config file in explorer.'


logger = script.get_logger()


PYREVIT_CORE_RELOAD_COMMAND_NAME = 'pyRevitCorepyRevitpyRevittoolsReload'


class SettingsWindow(forms.WPFWindow):
    """pyRevit Settings window that handles setting the pyRevit configs
    """

    def __init__(self, xaml_file_name):
        """Sets up the settings ui
        """

        forms.WPFWindow.__init__(self, xaml_file_name)
        try:
            self._setup_core_options()
        except Exception as setup_params_err:
            logger.error('Error setting up a parameter. Please update '
                         'pyRevit again. | {}'.format(setup_params_err))

        self._setup_user_extensions_list()
        self._setup_env_vars_list()

        # check boxes for each version of Revit
        # this could be automated but it pushed me to verify and test
        # before actually addin a new Revit version to the list
        self._addinfiles_cboxes = {'2015': self.revit2015_cb,
                                   '2016': self.revit2016_cb,
                                   '2017': self.revit2017_cb,
                                   '2018': self.revit2018_cb}

        self._setup_usagelogging()
        self._setup_addinfiles()

    def _setup_core_options(self):
        """Sets up the pyRevit core configurations
        """

        self.checkupdates_cb.IsChecked = user_config.core.checkupdates

        if not user_config.core.verbose and not user_config.core.debug:
            self.noreporting_rb.IsChecked = True
        else:
            self.debug_rb.IsChecked = user_config.core.debug
            self.verbose_rb.IsChecked = user_config.core.verbose

        self.filelogging_cb.IsChecked = user_config.core.filelogging

        self.startup_log_timeout.Text = str(user_config.core.startuplogtimeout)
        self.compilecsharp_cb.IsChecked = user_config.core.compilecsharp
        self.compilevb_cb.IsChecked = user_config.core.compilevb

        if user_config.core.bincache:
            self.bincache_rb.IsChecked = True
        else:
            self.asciicache_rb.IsChecked = True

        req_build = user_config.core.get_option('requiredhostbuild',
                                                default_value=0)
        self.requiredhostbuild_tb.Text = str(req_build)

        min_freespace = user_config.core.get_option('minhostdrivefreespace',
                                                    default_value=0)
        self.minhostdrivefreespace_tb.Text = str(min_freespace)

        self.loadbetatools_cb.IsChecked = \
            user_config.core.get_option('loadbeta', default_value=False)

        self.rocketmode_cb.IsChecked = user_config.core.rocketmode

        self.dynamocompatmode_cb.IsChecked = addinfiles.get_dynamocompat()

    def _setup_user_extensions_list(self):
        """Reads the user extension folders and updates the list
        """

        self.extfolders_lb.ItemsSource = user_config.core.userextensions

    def _setup_env_vars_list(self):
        """Reads the pyRevit environment variables and updates the list
        """
        class EnvVariable:
            """List item for an environment variable.

            Attributes:
                Id (str): Env Variable name
                Value (str): Env Variable value
            """

            def __init__(self, var_id, value):
                self.Id = var_id
                self.Value = value

            def __repr__(self):
                return '<EnvVariable Name: {} Value: {}>' \
                       .format(self.Id, self.Value)

        env_vars_list = [EnvVariable(k, v)
                         for k, v in envvars.get_pyrevit_env_vars().items()]

        self.envvars_lb.ItemsSource = env_vars_list

    def _setup_usagelogging(self):
        """Reads the pyRevit usage logging config and updates the ui
        """
        self.usagelogging_cb.IsChecked = \
            user_config.usagelogging.get_option('active',
                                                default_value=False)
        self.usagelogfile_tb.Text = \
            user_config.usagelogging.get_option('logfilepath',
                                                default_value='')
        self.usagelogserver_tb.Text = \
            user_config.usagelogging.get_option('logserverurl',
                                                default_value='')

        self.cur_usagelogfile_tb.Text = \
            usagelog.get_current_usage_logfile()
        self.cur_usagelogfile_tb.IsReadOnly = True
        self.cur_usageserverurl_tb.Text = \
            usagelog.get_current_usage_serverurl()
        self.cur_usageserverurl_tb.IsReadOnly = True

    def _setup_addinfiles(self):
        """Reads the state of pyRevit addin files for different Revit versions
        and updates the ui.
        """

        self.is_pyrevit_allusers = addinfiles.is_pyrevit_for_allusers()
        if self.is_pyrevit_allusers:
            addinfiles_states = addinfiles.get_addinfiles_state(allusers=True)
            self.revitversions_tb.Text = \
                str(self.revitversions_tb.Text).replace('%appdata%',
                                                        '%programdata%')
        else:
            addinfiles_states = addinfiles.get_addinfiles_state()

        for rvt_ver, checkbox in self._addinfiles_cboxes.items():
            if rvt_ver in addinfiles_states.keys():
                if rvt_ver != HOST_APP.version:
                    checkbox.IsEnabled = True
                    checkbox.IsChecked = addinfiles_states[rvt_ver]
                else:
                    checkbox.Content = 'Revit {} (Current version. ' \
                                       'Can not disable.)'.format(rvt_ver)
                    checkbox.IsEnabled = False
                    checkbox.IsChecked = True
            else:
                checkbox.Content = 'Revit {} (Not installed)'.format(rvt_ver)
                checkbox.IsChecked = checkbox.IsEnabled = False

    @staticmethod
    def update_usagelogging():
        """Updates the usage logging system per changes. This is usually
        called after new settings are saved and before pyRevit is reloaded.
        """
        usagelog.setup_usage_logfile()

    def update_addinfiles(self):
        """Enables/Disables the adding files for different Revit versions.
        """
        new_states = {rvt_ver: checkbox.IsChecked
                      for rvt_ver, checkbox in self._addinfiles_cboxes.items()}
        new_states.pop(HOST_APP.version)
        addinfiles.set_addinfiles_state(new_states,
                                        allusers=self.is_pyrevit_allusers)

    def resetreportinglevel(self, sender, args):
        """Callback method for resetting reporting (logging) levels to defaults
        """
        self.verbose_rb.IsChecked = True
        self.noreporting_rb.IsChecked = False
        self.debug_rb.IsChecked = False
        self.filelogging_cb.IsChecked = False

    def reset_requiredhostbuild(self, sender, args):
        """Callback method for resetting requried host version to current
        """
        self.requiredhostbuild_tb.Text = HOST_APP.build

    def resetcache(self, sender, args):
        """Callback method for resetting cache config to defaults
        """
        self.bincache_rb.IsChecked = True

    def copy_envvar_value(self, sender, args):
        """Callback method for copying selected env var value to clipboard
        """
        script.clipboard_copy(self.envvars_lb.SelectedItem.Value)

    def copy_envvar_id(self, sender, args):
        """Callback method for copying selected env var name to clipboard
        """
        script.clipboard_copy(self.envvars_lb.SelectedItem.Id)

    def addfolder(self, sender, args):
        """Callback method for adding extension folder to configs and list
        """
        new_path = forms.pick_folder()

        if new_path:
            new_path = os.path.normpath(new_path)

        if self.extfolders_lb.ItemsSource:
            uniq_items = set(self.extfolders_lb.ItemsSource)
            uniq_items.add(new_path)
            self.extfolders_lb.ItemsSource = list(uniq_items)
        else:
            self.extfolders_lb.ItemsSource = [new_path]

    def removefolder(self, sender, args):
        """Callback method for removing extension folder from configs and list
        """
        selected_path = self.extfolders_lb.SelectedItem
        if selected_path and self.extfolders_lb.ItemsSource:
            uniq_items = set(self.extfolders_lb.ItemsSource)
            uniq_items.remove(selected_path)
            self.extfolders_lb.ItemsSource = list(uniq_items)

    def removeallfolders(self, sender, args):
        """Callback method for removing all extension folders
        """
        self.extfolders_lb.ItemsSource = []

    def pick_usagelog_folder(self, sender, args):
        """Callback method for picking destination folder for usage log files
        """
        new_path = forms.pick_folder()

        if new_path:
            self.usagelogfile_tb.Text = os.path.normpath(new_path)

    def reset_usagelog_folder(self, sender, args):
        """Callback method for resetting usage log file folder to defaults
        """
        self.usagelogfile_tb.Text = usagelog.get_default_usage_logfilepath()

    def open_usagelog_folder(self, sender, args):
        """Callback method for opening destination folder for usage log files
        """
        cur_log_folder = op.dirname(self.cur_usagelogfile_tb.Text)
        if cur_log_folder:
            coreutils.open_folder_in_explorer(cur_log_folder)

    def savesettings(self, sender, args):
        """Callback method for saving pyRevit settings
        """

        # update the logging system changes first and update.
        if self.verbose_rb.IsChecked:
            logger.set_verbose_mode()
        if self.debug_rb.IsChecked:
            logger.set_debug_mode()

        # set config values to values set in ui items
        user_config.core.checkupdates = self.checkupdates_cb.IsChecked
        user_config.core.verbose = self.verbose_rb.IsChecked
        user_config.core.debug = self.debug_rb.IsChecked
        user_config.core.filelogging = self.filelogging_cb.IsChecked
        user_config.core.bincache = self.bincache_rb.IsChecked
        user_config.core.compilecsharp = self.compilecsharp_cb.IsChecked
        user_config.core.compilevb = self.compilevb_cb.IsChecked
        user_config.core.requiredhostbuild = self.requiredhostbuild_tb.Text

        try:
            min_freespace = int(self.minhostdrivefreespace_tb.Text)
            user_config.core.minhostdrivefreespace = min_freespace
        except ValueError:
            logger.error('Minimum free space value must be an integer.')
            user_config.core.minhostdrivefreespace = 0

        user_config.core.loadbeta = self.loadbetatools_cb.IsChecked
        user_config.core.startuplogtimeout = self.startup_log_timeout.Text
        user_config.core.rocketmode = self.rocketmode_cb.IsChecked

        # set extension folders from the list, after cleanup empty items
        if isinstance(self.extfolders_lb.ItemsSource, list):
            user_config.core.userextensions = \
                coreutils.filter_null_items(self.extfolders_lb.ItemsSource)
        else:
            user_config.core.userextensions = []

        # set usage logging configs
        user_config.usagelogging.active = self.usagelogging_cb.IsChecked
        user_config.usagelogging.logfilepath = self.usagelogfile_tb.Text
        user_config.usagelogging.logserverurl = self.usagelogserver_tb.Text

        # save all new values into config file
        user_config.save_changes()

        # set dynamo compatibility mode
        addinfiles.set_dynamocompat(self.dynamocompatmode_cb.IsChecked)
        # update usage logging and addin files
        self.update_usagelogging()
        self.update_addinfiles()
        self.Close()

    def savesettingsandreload(self, sender, args):
        """Callback method for saving pyRevit settings and reloading
        """
        self.savesettings(sender, args)

        from pyrevit.loader.sessionmgr import execute_command
        execute_command(PYREVIT_CORE_RELOAD_COMMAND_NAME)


# handles tool click in Revit interface:
# if Shift-Click on the tool, opens the pyRevit config file in
# windows explorer
# otherwise, will show the Settings user interface

if __shiftclick__:
    script.show_file_in_explorer(user_config.config_file)
else:
    SettingsWindow('SettingsWindow.xaml').show_dialog()
