"""Test Smart Button """
#pylint: disable=C0103,E0401
from pyrevit import script
from pyrevit.coreutils.ribbon import ICON_MEDIUM

__context__ = 'zero-doc'
__highlight__= 'updated'


config = script.get_config()


# FIXME: need to figure out a way to fix the icon sizing of toggle buttons
def __selfinit__(script_cmp, ui_button_cmp, __rvt__):
    on_icon = script_cmp.get_bundle_file('on.png')
    ui_button_cmp.set_icon(on_icon, icon_size=ICON_MEDIUM)


if __name__ == '__main__':
    print("Works...")
