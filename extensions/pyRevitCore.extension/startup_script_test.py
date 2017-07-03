"""Example of IronPython script to be executed by pyRevit on extension load

To Test:
- rename file to startup.py
- reload pyRevit: pyRevit will run this script after successfully
  created the DLL for the extension.

pyRevit runs the startup script in a dedicated IronPython engine and output
window. Thus the startup script is isolated and can not hurt the load process.
All errors will be printed to the dedicated output window similar to the way
errors are printed from pyRevit commands.
"""

# with open(r'C:\Temp\test.txt', 'w') as f:
#     f.write('test')

print('Startup script execution test.')