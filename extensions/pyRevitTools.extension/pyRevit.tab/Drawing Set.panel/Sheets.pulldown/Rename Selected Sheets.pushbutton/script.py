"""Change the selected sheet names."""

from pyrevit import revit, DB
from pyrevit import forms


def change_case(sheetlist, upper=True, verbose=False):
    with revit.Transaction('Rename Sheets to Upper'):
        for el in sheetlist:
            sheetnameparam = el.Parameter[DB.BuiltInParameter.SHEET_NAME]
            orig_name = sheetnameparam.AsString()
            new_name = orig_name.upper() if upper else orig_name.lower()
            if verbose:
                print('RENAMING:\t{0}\n'
                      '      to:\t{1}\n'.format(orig_name, new_name))
            sheetnameparam.Set(new_name)


sel_sheets = forms.select_sheets(title='Select Sheets', use_selection=True)

if sel_sheets:
    selected_option, switches = \
        forms.CommandSwitchWindow.show(
            ['to UPPERCASE',
             'to lowercase'],
            switches=['Show Report'],
            message='Select rename option:'
            )

    if selected_option:
        change_case(sel_sheets,
                    upper=True if selected_option == 'to UPPERCASE' else False,
                    verbose=switches['Show Report'])
