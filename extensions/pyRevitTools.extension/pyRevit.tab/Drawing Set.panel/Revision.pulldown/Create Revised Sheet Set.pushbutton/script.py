#pylint: disable=E0401,C0103,C0111
from pyrevit import revit
from pyrevit import forms, script


revisions = forms.select_revisions(button_name='Create Sheet Set',
                                   multiple=True)

if revisions:
    revision_names = [revision.Name for revision in revisions]
    if len(revisions) > 1:
        selected_switch = \
            forms.CommandSwitchWindow.show(['Matching ANY revision',
                                            'Matching ALL revisions'],
                                           message='Pick an option:')
        name_str = " & ".join(revision_names)
    else:
        selected_switch = 'Matching ALL revisions'
        name_str = revision_names[0]
    set_name = forms.ask_for_string(
        prompt='Enter a name for the new revision sheet set:',
        default=name_str,
        title='Revision Sheet Set',
        ok_text='Create',
        cancel_text='Cancel'
    )
    if set_name is None or set_name.strip() == '':
        forms.alert('Operation cancelled. No name was provided for the revision sheet set.')
        script.exit()
    if selected_switch:
        match_any = (selected_switch == 'Matching ANY revision')

        with revit.Transaction('Create Revision Sheet Set'):
            rev_sheetset = \
                revit.create.create_revision_sheetset(
                                                revisions,
                                                name_format=set_name,
                                                match_any=match_any
                    )

        empty_sheets = []
        for sheet in rev_sheetset:
            if revit.query.is_sheet_empty(sheet):
                empty_sheets.append(sheet)

        if empty_sheets:
            print('These sheets do not have any model contents and seem to be '
                  'placeholders for other content:')
            for esheet in empty_sheets:
                revit.report.print_sheet(esheet)
