"""Does its best at visually separating open documents."""
#pylint: disable=import-error,invalid-name,broad-except,superfluous-parens
from pyrevit.coreutils.ribbon import ICON_MEDIUM
from pyrevit import revit
from pyrevit import script


__title__ = 'Toggle\nInfoCenter'
__context__ = 'zero-doc'
__min_revit_ver__ = 2019


def __selfinit__(script_cmp, ui_button_cmp, __rvt__):
    button_icon = script_cmp.get_bundle_file(
        'on.png' if revit.ui.is_infocenter_visible() else 'off.png'
        )
    ui_button_cmp.set_icon(button_icon, icon_size=ICON_MEDIUM)


if __name__ == "__main__":
    state = revit.ui.toggle_infocenter()
    script.toggle_icon(state)
