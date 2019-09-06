"""Select title blocks on selected sheets for batch editing."""

from pyrevit import coreutils
from pyrevit import revit, DB
from pyrevit import forms
from pyrevit import script


logger = script.get_logger()


def get_source_sheets():
    sheet_elements = forms.select_sheets(button_name='Select TitleBlocks', use_selection=True)
    if not sheet_elements:
        script.exit()
    return sheet_elements


def select_titleblocks(sheets):
    all_tblocks = []
    for sheet in sheets:
        all_tblocks.extend(revit.query.get_sheet_tblocks(sheet))
    return all_tblocks


# orchestrate
sheets = get_source_sheets()
tblocks = select_titleblocks(sheets)
revit.get_selection().set_to(tblocks)
