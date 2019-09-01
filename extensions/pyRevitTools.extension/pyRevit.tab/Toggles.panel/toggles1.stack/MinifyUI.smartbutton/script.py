"""Reduce the list of open Revit tabs.

Shift+Click:
Customize which tabs should be hidden in minified mode.
"""
#pylint: disable=C0103,E0401
from pyrevit import script
from pyrevit.coreutils.ribbon import ICON_MEDIUM


__title__ = 'Minify\nRevit UI'
__context__ = 'zero-doc'


config = script.get_config()


# FIXME: need to figure out a way to fix the icon sizing of toggle buttons
def __selfinit__(script_cmp, ui_button_cmp, __rvt__):
    off_icon = script_cmp.get_bundle_file('off.png')
    ui_button_cmp.set_icon(off_icon, icon_size=ICON_MEDIUM)


if __name__ == '__main__':
    import minifyui
    minifyui.toggle_minifyui(config)
