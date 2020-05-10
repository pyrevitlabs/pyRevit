# pylint: disable=import-error,invalid-name,attribute-defined-outside-init
"""Applies the copied state to the active view.
This works in conjunction with the Copy State tool.

Shift-Click:
Show additional options
"""
from pyrevit import PyRevitException
from pyrevit import forms, script

import copypastestate


__authors__ = ['Gui Talarico', '{{author}}', 'Alex Melnikov']


# collect actions that are valid in this context
available_actions = [
    x for x in copypastestate.get_actions()
    if x.validate_context() and script.data_exists(x.__name__)
]

if available_actions:
    if len(available_actions) > 1:
        action_options = {x.name: x for x in available_actions}
        selected_action = \
            forms.CommandSwitchWindow.show(
                action_options.keys(),
                message='Select property to be pasted:',
                name_attr='name'
                )
        if selected_action:
            action = action_options[selected_action]
    else:
        action = available_actions[0]

    if action:
        try:
            action().paste()
        except PyRevitException as ex:
            forms.alert(ex.msg)
else:
    forms.alert('No available actions for this view or no saved'
                ' data found. Use "Copy State" first.')
