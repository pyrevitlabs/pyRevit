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
<<<<<<< Updated upstream
        minifyui.ensure_subscribed(config)
=======
>>>>>>> Stashed changes
        minifyui.update_ui(config)
    else:
        off_icon = ui.resolve_icon_file(
            script_cmp.directory, exts.DEFAULT_OFF_ICON_FILE)
        ui_button_cmp.set_icon(off_icon, icon_size=ICON_MEDIUM)


if __name__ == '__main__':
<<<<<<< Updated upstream
    minifyui.toggle_minifyui(config)
=======
    from pyrevit import EXEC_PARAMS

    if EXEC_PARAMS.debug_mode:
        # Ctrl+Click: run DLL diagnostic
        output = script.get_output()
        output.print_md('## MinifyUI DLL Diagnostic')

        # check 1: can we import types?
        try:
            from pyrevit.runtime import types
            output.print_md('- `types` import: **OK**')
        except Exception as ex:
            output.print_md('- `types` import: **FAILED** `{}`'.format(ex))

        # check 2: does RibbonTabVisibilityUtils exist?
        try:
            cls = types.RibbonTabVisibilityUtils
            output.print_md(
                '- `RibbonTabVisibilityUtils`: **FOUND** `{}`'.format(cls))
        except AttributeError:
            output.print_md(
                '- `RibbonTabVisibilityUtils`: **NOT FOUND** '
                '— wrong DLL loaded!')
        except Exception as ex:
            output.print_md(
                '- `RibbonTabVisibilityUtils`: **ERROR** `{}`'.format(ex))

        # check 3: which DLL is loaded?
        try:
            from pyrevit.runtime import RUNTIME_ASSM
            output.print_md('- Runtime assembly: `{}`'.format(RUNTIME_ASSM))
            output.print_md('- Location: `{}`'.format(
                RUNTIME_ASSM.Location))
        except Exception as ex:
            output.print_md('- Runtime assembly: **ERROR** `{}`'.format(ex))

        # check 4: DLL file timestamp
        try:
            import os
            dll_path = RUNTIME_ASSM.Location
            mtime = os.path.getmtime(dll_path)
            import datetime
            ts = datetime.datetime.fromtimestamp(mtime)
            output.print_md('- DLL modified: `{}`'.format(ts))
        except Exception as ex:
            output.print_md('- DLL timestamp: **ERROR** `{}`'.format(ex))

        # check 5: can we write to the log path?
        try:
            import os
            appdata = os.environ.get('APPDATA', '')
            log_dir = os.path.join(appdata, 'pyRevit')
            log_path = os.path.join(log_dir, 'MinifyUI_trace.log')
            output.print_md('- Log path: `{}`'.format(log_path))
            output.print_md('- Dir exists: `{}`'.format(
                os.path.exists(log_dir)))
            output.print_md('- Log exists: `{}`'.format(
                os.path.exists(log_path)))
        except Exception as ex:
            output.print_md('- Log path check: **ERROR** `{}`'.format(ex))
    else:
        minifyui.toggle_minifyui(config)
>>>>>>> Stashed changes
