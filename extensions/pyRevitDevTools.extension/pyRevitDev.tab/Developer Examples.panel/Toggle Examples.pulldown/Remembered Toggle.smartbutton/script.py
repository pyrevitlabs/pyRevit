"""Developer example: a smart button toggle that remembers its state.

pyRevit runs this file when it loads the button and calls __selfinit__,
which shows the saved state. The code under `if __name__ == "__main__":`
is the click: it flips the state, saves it in the pyRevit user config and
switches the icon. Code at the top level runs on both, so it only defines
names.
"""

import pyrevit.extensions as exts
from pyrevit import script
from pyrevit.coreutils.ribbon import ICON_MEDIUM
from pyrevit.revit import ui

CONFIG_SECTION = "devtools_examples"
STATE_OPTION = "remembered_toggle"


def is_on():
    config = script.get_config(CONFIG_SECTION)
    return bool(config.get_option(STATE_OPTION, default_value=False))


def __selfinit__(script_cmp, ui_button_cmp, __rvt__):
    icon_file = exts.DEFAULT_ON_ICON_FILE if is_on() else exts.DEFAULT_OFF_ICON_FILE
    ui_button_cmp.set_icon(
        ui.resolve_icon_file(script_cmp.directory, icon_file), icon_size=ICON_MEDIUM
    )
    return True


if __name__ == "__main__":
    new_state = not is_on()
    config = script.get_config(CONFIG_SECTION)
    config.set_option(STATE_OPTION, new_state)
    script.save_config()
    script.toggle_icon(new_state)
