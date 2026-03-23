"""Reduce the list of open Revit tabs.

Shift+Click:
Customize which tabs should be hidden in minified mode.
"""
#pylint: disable=C0103,E0401
from pyrevit import framework
from pyrevit import script
from pyrevit.revit import ui
from pyrevit import UI
import pyrevit.extensions as exts
from pyrevit.coreutils.ribbon import ICON_MEDIUM

import minifyui


logger = script.get_logger()

config = script.get_config()


def _on_view_activated(sender, args):
    """Re-apply minify tab visibility after every view switch.

    Revit (and its add-ins) can restore contextual tabs like Steel,
    Precast, Massing & Site during ViewActivated. This handler
    re-hides them if Minify is active.
    See: https://github.com/pyrevitlabs/pyRevit/issues/3106
    """
    try:
        if script.get_envvar(minifyui.MINIFYUI_ENV_VAR):
            minifyui.update_ui(config)
    except Exception as ex:
        logger.debug('MinifyUI view-activated handler error: %s', ex)


# FIXME: need to figure out a way to fix the icon sizing of toggle buttons
def __selfinit__(script_cmp, ui_button_cmp, __rvt__):
    # --- restore icon + visibility from persisted env state on reload ---
    is_active = script.get_envvar(minifyui.MINIFYUI_ENV_VAR)
    if is_active:
        on_icon = ui.resolve_icon_file(
            script_cmp.directory, exts.DEFAULT_ON_ICON_FILE)
        ui_button_cmp.set_icon(on_icon, icon_size=ICON_MEDIUM)
        minifyui.update_ui(config)
    else:
        off_icon = ui.resolve_icon_file(
            script_cmp.directory, exts.DEFAULT_OFF_ICON_FILE)
        ui_button_cmp.set_icon(off_icon, icon_size=ICON_MEDIUM)

    # --- subscribe to ViewActivated for the lifetime of this session ---
    # Handler checks MINIFYUIACTIVE internally, so it's safe to
    # subscribe unconditionally (same pattern as Sync Views smartbutton).
    try:
        __rvt__.ViewActivated += \
            framework.EventHandler[
                UI.Events.ViewActivatedEventArgs](_on_view_activated)
    except Exception as ex:
        logger.debug('MinifyUI: failed to attach ViewActivated handler: %s', ex)

    return True


if __name__ == '__main__':
    minifyui.toggle_minifyui(config)
