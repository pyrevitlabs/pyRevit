"""Exports selected schedules to TXT files on user desktop.

Shift-Click:
Rename files on Desktop
"""


import os
import os.path as op

from pyrevit import forms
from pyrevit import coreutils
from pyrevit import revit, DB


# if user shift-clicks, default to user desktop,
# otherwise ask for a folder containing the PDF files
if __shiftclick__:
    basefolder = op.expandvars('%userprofile%\\desktop')
else:
    basefolder = forms.pick_folder()


def is_schedule(view):
    """Filter schedule views."""
    if isinstance(view, DB.ViewSchedule):
        isrevsched = view.IsTitleblockRevisionSchedule
        isintkeynote = view.IsInternalKeynoteSchedule
        iskeynotelegend = view.Definition.CategoryId == \
            revit.query.get_category('Keynote Tags').Id

        return not (isrevsched or isintkeynote or iskeynotelegend)

    return False


schedules_to_export = forms.select_views(title='Select Schedules',
                                         filterfunc=is_schedule)

if schedules_to_export:
    vseop = DB.ViewScheduleExportOptions()
    vseop.ColumnHeaders = DB.ExportColumnHeaders.None
    vseop.TextQualifier = DB.ExportTextQualifier.DoubleQuote
    vseop.FieldDelimiter = ','
    vseop.Title = False
    vseop.HeadersFootersBlanks = False

    for sched in schedules_to_export:
        fname = "".join(x for x in sched.ViewName if x not in ['*']) + '.csv'
        sched.Export(basefolder, fname, vseop)
        coreutils.correct_revittxt_encoding(op.join(basefolder, fname))
        print('EXPORTED: {0}\n      TO: {1}\n'.format(sched.ViewName, fname))
