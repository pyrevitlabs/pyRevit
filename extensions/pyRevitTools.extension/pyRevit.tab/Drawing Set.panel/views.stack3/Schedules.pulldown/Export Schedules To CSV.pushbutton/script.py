"""Exports selected schedules to CSV files.

Shift-Click:
Pick from default output locations.
"""
#pylint: disable=C0103,E0401

import os.path as op

from pyrevit import forms
from pyrevit import coreutils
from pyrevit import revit, DB
from pyrevit import script


logger = script.get_logger()
output = script.get_output()


open_exported = False
basefolder = ''
# if user shift-clicks, default to user desktop,
# otherwise ask for a folder containing the PDF files
if __shiftclick__:  #pylint: disable=E0602
    destopt, switches = forms.CommandSwitchWindow.show(
        ["My Desktop", "Where Revit Model Is", "My Downloads"],
        switches=["Open CSV File"],
        message="Select destination:")
    if destopt == "My Desktop":
        basefolder = op.expandvars('%userprofile%\\desktop')
    if destopt == "My Downloads":
        basefolder = op.expandvars('%userprofile%\\downloads')
    elif destopt == "Where Revit Model Is":
        central_path = revit.query.get_central_path()
        if central_path:
            basefolder = op.dirname(central_path)
        else:
            basefolder = revit.query.get_project_info().location
            if not basefolder:
                forms.alert("Project has not been saved yet.", exitscript=True)

    open_exported = switches["Open CSV File"]
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


if basefolder:
    logger.debug(basefolder)
    schedules_to_export = forms.select_views(title="Select Schedules",
                                             filterfunc=is_schedule)

    if schedules_to_export:
        vseop = DB.ViewScheduleExportOptions()
        vseop.ColumnHeaders = coreutils.get_enum_none(DB.ExportColumnHeaders)
        vseop.TextQualifier = DB.ExportTextQualifier.DoubleQuote
        vseop.FieldDelimiter = ','
        vseop.Title = False
        vseop.HeadersFootersBlanks = False

        for sched in schedules_to_export:
            fname = \
                coreutils.cleanup_filename(revit.query.get_name(sched)) + '.csv'
            sched.Export(basefolder, fname, vseop)
            exported = op.join(basefolder, fname)
            coreutils.correct_revittxt_encoding(exported)
            output.print_md("**EXPORTED:** {0}"
                            .format(revit.query.get_name(sched)))
            print(exported)
            if open_exported:
                coreutils.run_process('"%s"' % exported)
