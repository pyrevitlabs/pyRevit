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

from pyrevit.userconfig import user_config


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


if basefolder:
    logger.debug(basefolder)
    schedules_to_export = forms.select_schedules()

    if schedules_to_export:
        vseop = DB.ViewScheduleExportOptions()
        vseop.ColumnHeaders = coreutils.get_enum_none(DB.ExportColumnHeaders)
        vseop.TextQualifier = DB.ExportTextQualifier.DoubleQuote

        # determine which separator to use
        csv_sp = ','
        regional_sep = user_config.get_list_separator()
        if regional_sep != ',':
            if forms.alert("Regional settings list separator is \"{}\"\n"
                           "Do you want to use this instead of comma?"
                           .format(regional_sep), yes=True, no=True):
                csv_sp = regional_sep

        if csv_sp:
            vseop.FieldDelimiter = csv_sp
            vseop.Title = False
            vseop.HeadersFootersBlanks = False

            for sched in schedules_to_export:
                fname = \
                    coreutils.cleanup_filename(revit.query.get_name(sched)) \
                    + '.csv'
                sched.Export(basefolder, fname, vseop)
                exported = op.join(basefolder, fname)
                coreutils.correct_revittxt_encoding(exported)
                output.print_md("**EXPORTED:** {0}"
                                .format(revit.query.get_name(sched)))
                print(exported)
                if open_exported:
                    coreutils.run_process('"%s"' % exported)
