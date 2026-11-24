# -*- coding: utf-8 -*-
"""Copy a property of the active view or the selection to memory, for Paste State."""

from pyrevit import PyRevitException
from pyrevit import forms

import copypastestate
from copypastestate.strings import text


def main():
    available_actions = [
        action for action in copypastestate.get_actions() if action.validate_context()
    ]
    if not available_actions:
        forms.alert(text("nothing_to_copy"), exitscript=True)
    action_by_name = {action.name: action for action in available_actions}
    selected_name = forms.CommandSwitchWindow.show(
        [action.name for action in available_actions],
        message=text("copy_prompt"),
        width=int(text("copy_window_width")),
    )
    if not selected_name:
        return
    try:
        action_by_name[selected_name]().copy()
    except PyRevitException as ex:
        forms.alert(ex.msg)


if __name__ == "__main__":
    main()
