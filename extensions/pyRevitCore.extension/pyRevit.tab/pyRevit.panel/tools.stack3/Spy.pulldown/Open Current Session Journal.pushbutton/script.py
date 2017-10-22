"""Increases the sheet number of the selected sheets by one."""

import os
import os.path as op

from pyrevit import revit


# Checks to see if notepad++ program is installed and available.
def npplusplus_exists():
    pffolder = os.getenv('ProgramFiles(x86)')
    return op.isfile(op.join(pffolder, 'Notepad++\\Notepad++.EXE'))


current_journal = revit.get_current_journal_file()

if npplusplus_exists():
    os.system('start notepad++ -lvb -n9999999999 "{0}"'
              .format(current_journal))
else:
    os.system('start notepad "{0}"'.format(current_journal))
