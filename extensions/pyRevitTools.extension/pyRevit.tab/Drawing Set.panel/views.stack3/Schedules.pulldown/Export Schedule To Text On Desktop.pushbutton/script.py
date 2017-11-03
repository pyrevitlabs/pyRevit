"""Exports selected schedules to TXT files on user desktop.

Shift-Click:
Rename files on Desktop
"""


import os
import os.path as op

from pyrevit import forms
from pyrevit import revit, DB


# if user shift-clicks, default to user desktop,
# otherwise ask for a folder containing the PDF files
if __shiftclick__:
    basefolder = op.expandvars('%userprofile%\\desktop')
else:
    basefolder = forms.pick_folder()


vseop = DB.ViewScheduleExportOptions()
# vseop.ColumnHeaders = DB.ExportColumnHeaders.None
# vseop.TextQualifier = DB.ExportTextQualifier.None
# vseop.FieldDelimiter = ','
# vseop.Title = False

for el in revit.get_selection():
    fname = "".join(x for x in el.ViewName if x not in ['*']) + '.txt'
    el.Export(basefolder, fname, vseop)
    print('EXPORTED: {0}\n      TO: {1}\n'.format(el.ViewName, fname))
