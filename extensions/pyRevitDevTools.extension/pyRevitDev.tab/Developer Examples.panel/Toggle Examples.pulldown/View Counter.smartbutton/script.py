"""Developer example: a smart button that listens to a Revit event.

__selfinit__ subscribes a ViewActivated handler through
events.replace_handler, which first removes the handler that the previous
pyRevit load subscribed, so a reload never leaves two handlers running. If
the subscription fails, __selfinit__ returns False and the button is
disabled.

The handler runs outside the button's bundle and without the folders the
script added to sys.path, so everything it uses is imported at the top of
this file. The on/off state and the count live in pyRevit environment
variables: they last for the Revit session, and the handler and the click
both see them.
"""

import pyrevit.extensions as exts
from pyrevit import UI, script
from pyrevit.coreutils.ribbon import ICON_MEDIUM
from pyrevit.revit import events, ui

ACTIVE_VAR = "DEVTOOLSVIEWCOUNTERACTIVE"
COUNT_VAR = "DEVTOOLSVIEWCOUNTERCOUNT"
HANDLER_SLOT = "pyRevitDevTools.ViewCounter.ViewActivated"

logger = script.get_logger()


def count_activated_view(sender, args):
    if script.get_envvar(ACTIVE_VAR):
        script.set_envvar(COUNT_VAR, (script.get_envvar(COUNT_VAR) or 0) + 1)


def __selfinit__(script_cmp, ui_button_cmp, __rvt__):
    try:
        events.replace_handler(
            HANDLER_SLOT,
            __rvt__,
            "ViewActivated",
            count_activated_view,
            UI.Events.ViewActivatedEventArgs,
        )
    except Exception as subscribe_error:
        logger.error("View Counter could not subscribe: %s", subscribe_error)
        return False

    is_on = bool(script.get_envvar(ACTIVE_VAR))
    icon_file = exts.DEFAULT_ON_ICON_FILE if is_on else exts.DEFAULT_OFF_ICON_FILE
    ui_button_cmp.set_icon(
        ui.resolve_icon_file(script_cmp.directory, icon_file), icon_size=ICON_MEDIUM
    )
    return True


if __name__ == "__main__":
    turning_on = not script.get_envvar(ACTIVE_VAR)
    if turning_on:
        script.set_envvar(COUNT_VAR, 0)
        print("Counting activated views. Click View Counter again to stop.")
    else:
        print(
            "{} views were activated while counting.".format(
                script.get_envvar(COUNT_VAR) or 0
            )
        )
    script.set_envvar(ACTIVE_VAR, turning_on)
    script.toggle_icon(turning_on)
