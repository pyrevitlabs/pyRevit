# -*- coding: utf-8 -*-
"""Configuration dialog for the Custom Properties dockable pane.

Shift-click the button to open this dialog.
"""

from pyrevit import forms, script
from pyrevit.coreutils import applocales

from panes.customprops.pane import (
    CONFIG_SECTION,
    WS_POSTFIX,
    ADD_PARAMS,
    SHOW_WS_INFO,
    CustomPropertiesPanel,
)

RESTART_REQUIRED = {
    "en_us": "Restart Revit for the startup change to take effect.",
    "de_de": "Starten Sie Revit neu, damit die Änderung beim Start wirksam wird.",
    "fr_fr": "Redémarrez Revit pour que la modification du démarrage soit prise en compte.",
    "es_es": "Reinicie Revit para que el cambio de inicio surta efecto.",
    "pt_br": "Reinicie o Revit para que a alteração de inicialização tenha efeito.",
    "ru": "Перезапустите Revit, чтобы изменение автозагрузки вступило в силу.",
    "chinese_s": "请重新启动 Revit 以使启动更改生效。",
    "ko": "시작 설정 변경 사항을 적용하려면 Revit을 다시 시작하세요.",
}


class ConfigWindow(forms.WPFWindow):
    resolve_theme = True

    def __init__(self, xaml_path):
        forms.WPFWindow.__init__(self, xaml_path)
        self.my_config = script.get_config(CONFIG_SECTION)
        self._load_current()

    def _load_current(self):
        raw = self.my_config.get_option(ADD_PARAMS, "")
        self.params_tb.Text = raw
        enabled = self.my_config.get_option("enabled", False)
        self.enable_cb.IsChecked = bool(enabled)
        self._original_enabled = bool(enabled)
        show_worksharing = self.my_config.get_option(SHOW_WS_INFO, True)
        self.worksharing_cb.IsChecked = bool(show_worksharing)

    def save_clicked(self, sender, args):
        self.my_config.set_option(ADD_PARAMS, self.params_tb.Text)
        new_enabled = bool(self.enable_cb.IsChecked)
        self.my_config.set_option("enabled", new_enabled)
        self.my_config.set_option(SHOW_WS_INFO, bool(self.worksharing_cb.IsChecked))
        script.save_config()
        script.set_envvar(CONFIG_SECTION, self.params_tb.Text)
        script.set_envvar(
            CONFIG_SECTION + WS_POSTFIX, bool(self.worksharing_cb.IsChecked)
        )
        startup_changed = new_enabled != self._original_enabled
        self.Close()
        if startup_changed:
            forms.alert(
                applocales.get_locale_string(RESTART_REQUIRED),
                title=CustomPropertiesPanel.panel_title,
            )

    def cancel_clicked(self, sender, args):
        self.Close()


ConfigWindow("config_ui.xaml").ShowDialog()
