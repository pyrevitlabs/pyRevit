from pyrevit import framework
from pyrevit import revit, DB
from pyrevit import forms


__author__ = '{{author}}'
__doc__ = 'Select a revision from the list of revisions and this script '\
          'will create a print sheet set for the revised sheets under the '\
          'selected revision, and will assign the new sheet set as '\
          'the default print set.'


revisions = forms.select_revisions(button_name='Create Sheet Set',
                                   multiple=True)
if revisions:
    with revit.Transaction('Create Revision Sheet Set'):
        rev_sheetset = revit.create.create_revision_sheetset(revisions)

    empty_sheets = []
    for sheet in rev_sheetset:
        if revit.query.is_sheet_empty(sheet):
            empty_sheets.append(sheet)

    if empty_sheets:
        print('These sheets do not have any contents and seem to be '
              'placeholders for other content:')
        for esheet in empty_sheets:
            revit.report.print_sheet(sheet)
