# -*- coding: utf-8 -*-
"""Reduce the list of open Revit tabs.

Shift+Click:
Customize which tabs should be hidden in minified mode.
"""
#pylint: disable=C0103,E0401
from pyrevit import script
from pyrevit.revit import ui
import pyrevit.extensions as exts
from pyrevit.coreutils.ribbon import ICON_MEDIUM

import minifyui


config = script.get_config()


# FIXME: need to figure out a way to fix the icon sizing of toggle buttons
def __selfinit__(script_cmp, ui_button_cmp, __rvt__):
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


if __name__ == '__main__':
    minifyui.toggle_minifyui(config)
