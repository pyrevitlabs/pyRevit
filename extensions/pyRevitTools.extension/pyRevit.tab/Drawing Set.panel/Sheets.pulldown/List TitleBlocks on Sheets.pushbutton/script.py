"""Select title blocks on selected sheets for batch editing."""
# pylint: disable=import-error,invalid-name,broad-except,superfluous-parens
from pyrevit import revit
from pyrevit import forms
from pyrevit import script

output = script.get_output()
logger = script.get_logger()


def get_source_sheets():
    sheet_elements = forms.select_sheets(
        button_name="List TitleBlocks",
        use_selection=True,
        include_placeholder=False,
    )
    if not sheet_elements:
        script.exit()
    return sheet_elements


def print_titleblocks(sheets):
    all_tblocks = []
    for sheet in sheets:
        tblocks = revit.query.get_sheet_tblocks(sheet)
        all_tblocks.extend([x.Id for x in tblocks])
        for tblock in tblocks:
            print(
                "SHEET: {0} - {1}\t\tTITLEBLOCK: {2} {3}".format(
                    sheet.SheetNumber,
                    sheet.Name,
                    tblock.Name,
                    output.linkify(tblock.Id),
                )
            )
    print(
        "{}".format(output.linkify(all_tblocks, title="Select All TitleBlocks"))
    )


# orchestrate
print_titleblocks(get_source_sheets())
