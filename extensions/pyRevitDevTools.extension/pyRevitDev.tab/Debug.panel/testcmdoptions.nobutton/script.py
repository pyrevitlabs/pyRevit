from pyrevit import forms

__context__ = 'zero-doc'


selected_switch, switches = \
    forms.CommandSwitchWindow.show(['Example Option 1 (help)',
                                    'Example Option 2 (run)',
                                    'Example Option 3 (batch)'],
                                   switches=['Switch 1', 'Switch 2'])

print('No GUI Command'
      '\n Selected Option: {}'
      '\n Switch 1 = {}'
      '\n Switch 2 = {}'.format(selected_switch,
                                switches['Switch 1'],
                                switches['Switch 2']))
