from pyrevit import forms

__context__ = 'zerodoc'


selected_switch = \
    forms.CommandSwitchWindow.show(['Example Option 1 (help)',
                                    'Example Option 2 (run)',
                                    'Example Option 3 (batch)'])

print('No GUI Command: {}'.format(selected_switch))
