"""Example of IronPython script to be executed by pyRevit on extension load

The script filename must end in startup.py

To Test:
- rename file to startup.py
- reload pyRevit: pyRevit will run this script after successfully
  created the DLL for the extension.

pyRevit runs the startup script in a dedicated IronPython engine and output
window. Thus the startup script is isolated and can not hurt the load process.
All errors will be printed to the dedicated output window similar to the way
errors are printed from pyRevit commands.
"""

import sys

# add your module paths to the sys.path here
# sys.path.append(r'path/to/your/module')

print('Startup script execution test.')
print('\n'.join(sys.path))

# test imports from same directory and exensions lib
import startupimport
import startuplibimport

# example code for creating event handlers
# from pyrevit import HOST_APP, framework
# from pyrevit import DB
# from pyrevit import forms

# define event handler
# def docopen_eventhandler(sender, args):
#     forms.alert('Document Opened: {}'.format(args.PathName))

# add to DocumentOpening
# type is EventHandler[DocumentOpeningEventArgs] so create that correctly
# HOST_APP.app.DocumentOpening += \
#     framework.EventHandler[DB.Events.DocumentOpeningEventArgs](
#         docopen_eventhandler
#         )
