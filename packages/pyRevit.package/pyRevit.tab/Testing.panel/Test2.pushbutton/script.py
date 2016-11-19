__context__ = 'Walls'

if __shiftclick__:
    print('Shif-Clicked button')

import pyrevit.scriptutils as su
script = su.get_script_info(__file__)
print script.cmd_context