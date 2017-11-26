from pyrevit.framework import List
from pyrevit import revit, DB
from pyrevit import forms


__doc__ = 'Select a revision from the list of revisions\n'\
          'and this script will remove that revision ' \
          'from all sheets if it has not been "clouded" on the sheet.'


def remove_rev_from_sheets(revision_element, sheets=None):
    if not sheets:
        # collect data
        sheets = DB.FilteredElementCollector(revit.doc)\
                   .OfCategory(DB.BuiltInCategory.OST_Sheets)\
                   .WhereElementIsNotElementType()\
                   .ToElements()

    cloudedsheets = []
    affectedsheets = []
    with revit.Transaction('Remove Revision from Sheets'):
        for s in sheets:
            revs = set([x.IntegerValue for x in s.GetAllRevisionIds()])
            addrevs = set([x.IntegerValue
                           for x in s.GetAdditionalRevisionIds()])
            cloudrevs = revs - addrevs
            if revision_element.Id.IntegerValue in cloudrevs:
                cloudedsheets.append(s)
                continue
            elif len(addrevs) > 0:
                addrevs.remove(revision_element.Id.IntegerValue)
                revelids = [DB.ElementId(x) for x in addrevs]
                s.SetAdditionalRevisionIds(List[DB.ElementId](revelids))
                affectedsheets.append(s)

    if len(affectedsheets) > 0:
        print('SELECTED REVISION REMOVED FROM THESE SHEETS:')
        print('-' * 100)
        for s in affectedsheets:
            snum = s.LookupParameter('Sheet Number').AsString().rjust(10)
            sname = s.LookupParameter('Sheet Name').AsString().ljust(50)
            print('NUMBER: {0}   NAME:{1}'.format(snum, sname))

    if len(cloudedsheets) > 0:
        print('SELECTED REVISION IS CLOUDED ON THESE SHEETS '
              'AND CAN NOT BE REMOVED.')
        print('-' * 100)

        for s in cloudedsheets:
            snum = s.LookupParameter('Sheet Number').AsString().rjust(10)
            sname = s.LookupParameter('Sheet Name').AsString().ljust(50)
            print('NUMBER: {0}   NAME:{1}'.format(snum, sname))


revision = forms.select_revisions(button_name='Remove Revision',
                                  multiselect=False)
if revision:
    remove_rev_from_sheets(revision)
