# -*- coding: utf-8 -*-
"""Configuration dialog for the Custom Properties dockable pane.

Shift-click the button to open this dialog.
"""
from pyrevit import forms, script

from panes.customprops.pane import CONFIG_SECTION


class ConfigWindow(forms.WPFWindow):
    def __init__(self, xaml_path):
        forms.WPFWindow.__init__(self, xaml_path)
        self.my_config = script.get_config(CONFIG_SECTION)
        self._load_current()

    def _load_current(self):
        raw = self.my_config.get_option("additional_parameters", "")
        self.params_tb.Text = raw
        enabled = self.my_config.get_option("enabled", False)
        self.enable_cb.IsChecked = bool(enabled)
        self._original_enabled = bool(enabled)
        show_worksharing = self.my_config.get_option("show_worksharing_info", True)
        self.worksharing_cb.IsChecked = bool(show_worksharing)

    def save_clicked(self, sender, args):
        self.my_config.set_option("additional_parameters", self.params_tb.Text)
        new_enabled = bool(self.enable_cb.IsChecked)
        self.my_config.set_option("enabled", new_enabled)
        self.my_config.set_option(
            "show_worksharing_info", bool(self.worksharing_cb.IsChecked)
        )
        script.save_config()
        script.set_envvar(CONFIG_SECTION, self.params_tb.Text)
        script.set_envvar(CONFIG_SECTION+"_ws_info", bool(self.worksharing_cb.IsChecked))
        startup_changed = new_enabled != self._original_enabled
        self.Close()
        if startup_changed:
            forms.alert(
                "Restart Revit for the startup change to take effect.",
                title="Custom Properties",
            )

    def cancel_clicked(self, sender, args):
        self.Close()


ConfigWindow("config_ui.xaml").ShowDialog()
