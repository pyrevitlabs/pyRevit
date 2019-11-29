# pylint: disable=import-error,invalid-name,attribute-defined-outside-init
'Applies the copied state to the active view. '\
'This works in conjunction with the Copy State tool.'

import inspect
import copy_paste_state_actions
from pyrevit import forms
from pyrevit import script

__authors__ = ['Gui Talarico', '{{author}}']

logger = script.get_logger()

LAST_ACTION_VAR = "COPYPASTESTATE"

# main logic

available_actions = {}
# get available actions from copy_paste_state_actions
for mem in inspect.getmembers(copy_paste_state_actions):
    moduleobject = mem[1]
    if inspect.isclass(moduleobject) \
            and hasattr(moduleobject, 'is_copy_paste_action'):
        if hasattr(moduleobject, 'validate_context') \
                and not moduleobject.validate_context():
            available_actions[moduleobject.name] = moduleobject
# read last saved action from env var
last_action = script.get_envvar(LAST_ACTION_VAR)

# pylint: disable=undefined-variable
if last_action not in available_actions.keys() or __shiftclick__:
    selected_option = \
        forms.CommandSwitchWindow.show(
            available_actions.keys(),
            message='Select property to be copied to memory:')
else:
    selected_option = last_action

if selected_option:
    action = available_actions[selected_option]()
    action.paste_wrapper()
