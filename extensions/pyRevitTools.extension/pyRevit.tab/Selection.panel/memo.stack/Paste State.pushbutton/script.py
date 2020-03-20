# pylint: disable=import-error,invalid-name,attribute-defined-outside-init
"""Applies the copied state to the active view.
This works in conjunction with the Copy State tool.

Shift-Click:
Show additional options
"""
from pyrevit import PyRevitException
from pyrevit import forms

import copypastestate


__authors__ = ['Gui Talarico', '{{author}}', 'Alex Melnikov']


# collect actions that are valid in this context
available_actions = [
    x for x in copypastestate.get_actions() if x.validate_context()
]

if available_actions:
    action_options = {x.name: x for x in available_actions}
    selected_action = \
        forms.CommandSwitchWindow.show(
            action_options.keys(),
            message='Select property to be pasted:',
            name_attr='name'
            )

    if selected_action:
        action = action_options[selected_action]
        try:
            action().paste()
        except PyRevitException as ex:
            forms.alert(ex.msg)
