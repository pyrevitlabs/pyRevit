# -*- coding: utf-8 -*-
"""Reduce the list of open Revit tabs.

Shift+Click:
Customize which tabs should be hidden in minified mode.

Ctrl+Click:
Run diagnostic dump of ribbon tab info to pyRevit output.
"""
#pylint: disable=C0103,E0401
from pyrevit import script
from pyrevit.revit import ui
from pyrevit import EXEC_PARAMS
import pyrevit.extensions as exts
from pyrevit.coreutils.ribbon import ICON_MEDIUM

import minifyui


config = script.get_config()


def __selfinit__(script_cmp, ui_button_cmp, __rvt__):
    """Restore icon and re-subscribe if Minify was active."""
    is_active = script.get_envvar(minifyui.MINIFYUI_ENV_VAR)
    if is_active:
        on_icon = ui.resolve_icon_file(
            script_cmp.directory, exts.DEFAULT_ON_ICON_FILE)
        ui_button_cmp.set_icon(on_icon, icon_size=ICON_MEDIUM)
        minifyui.subscribe_handlers(config)
        minifyui.update_ui(config)
    else:
        off_icon = ui.resolve_icon_file(
            script_cmp.directory, exts.DEFAULT_OFF_ICON_FILE)
        ui_button_cmp.set_icon(off_icon, icon_size=ICON_MEDIUM)
    return True


if __name__ == '__main__':
    if EXEC_PARAMS.debug_mode:
        minifyui.dump_ribbon_info()
    else:
        minifyui.toggle_minifyui(config)
