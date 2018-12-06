"""Remove selected revisions from selected sheets."""

from pyrevit import revit, DB
from pyrevit import forms
from pyrevit import script


__doc__ = 'Select a revision from the list of revisions\n'\
          'and this script will remove that revision ' \
          'from all sheets if it has not been "clouded" on the sheet.'

logger = script.get_logger()


revisions = forms.select_revisions(button_name='Select Revision',
                                   multiple=True)

logger.debug(revisions)

if revisions:
    sheets = forms.select_sheets(button_name='Set Revision')
    if sheets:
        with revit.Transaction('Remove Revision from Sheets'):
            updated_sheets = revit.update.update_sheet_revisions(revisions,
                                                                 sheets,
                                                                 state=False)
        if updated_sheets:
            print('SELECTED REVISION REMOVED FROM THESE SHEETS:')
            print('-' * 100)
            cloudedsheets = []
            for s in sheets:
                if s in updated_sheets:
                    revit.report.print_sheet(s)
                else:
                    cloudedsheets.append(s)
        else:
            cloudedsheets = sheets

        if len(cloudedsheets) > 0:
            print('\n\nSELECTED REVISION IS CLOUDED ON THESE SHEETS '
                  'AND CAN NOT BE REMOVED.')
            print('-' * 100)

            for s in cloudedsheets:
                revit.report.print_sheet(s)
