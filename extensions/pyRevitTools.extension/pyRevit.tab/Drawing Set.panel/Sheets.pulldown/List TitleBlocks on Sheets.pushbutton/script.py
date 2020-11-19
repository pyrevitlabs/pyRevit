"""Select title blocks on selected sheets for batch editing."""

from pyrevit import coreutils
from pyrevit import revit, DB
from pyrevit import forms
from pyrevit import script

output = script.get_output()
logger = script.get_logger()


def get_source_sheets():
    sheet_elements = forms.select_sheets(button_name='Select TitleBlocks',
                                         use_selection=True,
                                         include_placeholder=False)
    if not sheet_elements:
        script.exit()
    return sheet_elements


def print_titleblocks(sheets):
    for sheet in sheets:
        tblocks = revit.query.get_sheet_tblocks(sheet)
        for tblock in tblocks:
            print('SHEET: {0} - {1}\t\tTITLEBLOCK: {2} {3}'.format(sheet.SheetNumber, sheet.Name, tblock.Name, output.linkify(tblock.Id)))


# orchestrate
sheets = get_source_sheets()
tblocks = print_titleblocks(sheets)