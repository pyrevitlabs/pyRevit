# -*- coding: utf-8 -*-
"""Toggle the Custom Properties dockable pane."""

from pyrevit import DB, UI, forms, script
from pyrevit.coreutils import applocales
from pyrevit.revit import events, ui
from pyrevit.framework import Threading, System
import pyrevit.extensions as exts
from pyrevit.coreutils.ribbon import ICON_MEDIUM

from panes.customprops.pane import CustomPropertiesPanel, CONFIG_SECTION

_PANEL_ID = CustomPropertiesPanel.panel_id
_DOC_OPENED_SLOT = "pyRevitTools.CustomProperties.DocumentOpened"
_VISIBILITY_SLOT = "pyRevitTools.CustomProperties.DockableFrameVisibilityChanged"
TOOL_DISABLED = {
    "en_us": "Tool disabled in config.",
    "de_de": "Das Werkzeug ist in der Konfiguration deaktiviert.",
    "fr_fr": "Outil désactivé dans la configuration.",
    "es_es": "Herramienta desactivada en la configuración.",
    "pt_br": "Ferramenta desativada na configuração.",
    "ru": "Инструмент отключён в настройках.",
    "chinese_s": "该工具已在配置中禁用。",
    "ko": "이 도구는 구성에서 비활성화되어 있습니다.",
}


def __selfinit__(script_cmp, ui_button_cmp, __rvt__):
    def set_icon(is_shown):
        if is_shown:
            icon = ui.resolve_icon_file(script_cmp.directory, exts.DEFAULT_ON_ICON_FILE)
        else:
            icon = ui.resolve_icon_file(
                script_cmp.directory, exts.DEFAULT_OFF_ICON_FILE
            )
        ui_button_cmp.set_icon(icon, icon_size=ICON_MEDIUM)

    def update_icon_from_pane():
        try:
            dockable = forms.get_dockable_panel(_PANEL_ID)
            set_icon(dockable.IsShown())
        except Exception:
            set_icon(False)

    def on_visibility_changed(sender, args):
        def deferred():
            update_icon_from_pane()

        Threading.Dispatcher.CurrentDispatcher.BeginInvoke(
            Threading.DispatcherPriority.Background, System.Action(deferred)
        )

    def watch_visibility():
        events.replace_handler(
            _VISIBILITY_SLOT,
            __rvt__,
            "DockableFrameVisibilityChanged",
            on_visibility_changed,
            UI.Events.DockableFrameVisibilityChangedEventArgs,
        )

    def wait_for_document():
        events.replace_handler(
            _DOC_OPENED_SLOT,
            __rvt__.Application,
            "DocumentOpened",
            on_document_opened,
            DB.Events.DocumentOpenedEventArgs,
        )

    def on_document_opened(sender, args):
        events.release_handler(_DOC_OPENED_SLOT, __rvt__.Application, "DocumentOpened")
        update_icon_from_pane()
        watch_visibility()

    set_icon(False)
    events.release_handler(_DOC_OPENED_SLOT, __rvt__.Application, "DocumentOpened")
    events.release_handler(_VISIBILITY_SLOT, __rvt__, "DockableFrameVisibilityChanged")

    try:
        if __rvt__.ActiveUIDocument is not None:
            update_icon_from_pane()
            watch_visibility()
        else:
            wait_for_document()
    except Exception:
        wait_for_document()

    return True


if __name__ == "__main__":
    my_config = script.get_config(CONFIG_SECTION)
    if not my_config.get_option("enabled", False):
        forms.alert(
            applocales.get_locale_string(TOOL_DISABLED),
            title=CustomPropertiesPanel.panel_title,
            exitscript=True,
        )
    dockable = forms.get_dockable_panel(_PANEL_ID)
    forms.toggle_dockable_panel(_PANEL_ID, not dockable.IsShown())
