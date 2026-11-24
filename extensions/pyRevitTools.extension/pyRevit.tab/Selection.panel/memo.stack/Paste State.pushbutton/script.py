# -*- coding: utf-8 -*-
"""Apply the property stored by Copy State to the active view or the selection."""

from pyrevit import PyRevitException
from pyrevit import forms, script

import copypastestate
from copypastestate.strings import text


def pasteable_actions():
    return [
        action
        for action in copypastestate.get_actions()
        if action.validate_context()
        and script.data_exists(action.__name__, this_project=action.this_project)
    ]


def choose_action(actions):
    if len(actions) == 1:
        return actions[0]
    action_by_name = {action.name: action for action in actions}
    selected_name = forms.CommandSwitchWindow.show(
        [action.name for action in actions],
        message=text("paste_prompt"),
        width=int(text("paste_window_width")),
    )
    if not selected_name:
        script.exit()
    return action_by_name[selected_name]


def main():
    actions = pasteable_actions()
    if not actions:
        forms.alert(text("nothing_to_paste"), exitscript=True)
    action = choose_action(actions)
    try:
        action().paste()
    except PyRevitException as ex:
        forms.alert(ex.msg)


if __name__ == "__main__":
    main()
