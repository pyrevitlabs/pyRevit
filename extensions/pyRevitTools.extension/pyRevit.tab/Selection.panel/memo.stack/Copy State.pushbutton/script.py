# pylint: disable=import-error,invalid-name,attribute-defined-outside-init
'Copies the state of desired parameter of the active'\
' view to memory. e.g. Visibility Graphics settings or'\
' Zoom state. Run it and see how it works.'

import inspect
from pyrevit import forms
from pyrevit import script
import copy_paste_state_actions

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

selected_option = \
    forms.CommandSwitchWindow.show(
        available_actions.keys(),
        message='Select property to be copied to memory:')
        
if selected_option:
    action = available_actions[selected_option]()
    action.copy_wrapper()
    script.set_envvar(LAST_ACTION_VAR, selected_option)
