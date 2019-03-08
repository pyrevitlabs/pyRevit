"""Change the selected sheet names."""
#pylint: disable=import-error,invalid-name
from pyrevit import revit
from pyrevit import forms

selection = revit.get_selection()
sel_sheets = forms.select_sheets(title='Select Sheets')

if sel_sheets:
    selection.set_to(sel_sheets)
