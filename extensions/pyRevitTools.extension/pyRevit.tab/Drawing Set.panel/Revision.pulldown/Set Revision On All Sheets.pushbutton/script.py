from pyrevit.framework import List
from pyrevit import revit, DB
from pyrevit import forms


__doc__ = 'Select a revision from the list of revisions and '\
          'this script set that revision on all sheets in the '\
          'model as an additional revision.'


def set_rev_on_sheets(revision_element, sheets=None):
    if not sheets:
        # collect data
        sheets = DB.FilteredElementCollector(revit.doc)\
                   .OfCategory(DB.BuiltInCategory.OST_Sheets)\
                   .WhereElementIsNotElementType()\
                   .ToElements()

    affectedsheets = []
    with revit.Transaction('Set Revision on Sheets'):
        for s in sheets:
            revs = list(s.GetAdditionalRevisionIds())
            revs.append(sr.Id)
            s.SetAdditionalRevisionIds(List[DB.ElementId](revs))
            affectedsheets.append(s)

    if len(affectedsheets) > 0:
        print('SELECTED REVISION ADDED TO THESE SHEETS:')
        print('-' * 100)
        for s in affectedsheets:
            snum = s.LookupParameter('Sheet Number').AsString().rjust(10)
            sname = s.LookupParameter('Sheet Name').AsString().ljust(50)
            print('NUMBER: {0}   NAME:{1}'.format(snum, sname))


revision = forms.select_revisions(button_name='Set Revision',
                                  multiselect=False)
if revision:
    set_rev_on_sheets(revision)
