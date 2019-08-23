#pylint: disable=E0401,C0103,C0111
from pyrevit import revit
from pyrevit import forms


__doc__ = 'Select a revision from the list of revisions and this script '\
          'will create a print sheet set for the revised sheets under the '\
          'selected revision, and will assign the new sheet set as '\
          'the default print set.'


revisions = forms.select_revisions(button_name='Create Sheet Set',
                                   multiple=True)
if revisions:
    if len(revisions) > 1:
        selected_switch = \
            forms.CommandSwitchWindow.show(['Matching ANY revision',
                                            'Matching ALL revisions'],
                                           message='Pick an option:')
    else:
        selected_switch = 'Matching ALL revisions'

    if selected_switch:
        match_any = (selected_switch == 'Matching ANY revision')
        with revit.Transaction('Create Revision Sheet Set'):
            rev_sheetset = \
                revit.create.create_revision_sheetset(revisions,
                                                      match_any=match_any)

        empty_sheets = []
        for sheet in rev_sheetset:
            if revit.query.is_sheet_empty(sheet):
                empty_sheets.append(sheet)

        if empty_sheets:
            print('These sheets do not have any model contents and seem to be '
                  'placeholders for other content:')
            for esheet in empty_sheets:
                revit.report.print_sheet(esheet)
