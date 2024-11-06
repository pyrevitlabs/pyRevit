from pyrevit import revit, DB
from pyrevit.compat import get_elementid_value_func


selection = revit.get_selection()

get_elementid_value = get_elementid_value_func()

selectedrevs = []
hasSelectedRevision = False
multipleRevs = False

for s in selection:
    if isinstance(s, DB.RevisionCloud):
        selectedrevs.append(get_elementid_value(s.RevisionId))

if len(selectedrevs) > 1:
    multipleRevs = True

print('REVISED SHEETS:\n\nNAME\tNUMBER\n' + '-'*70)

sheetsnotsorted = DB.FilteredElementCollector(revit.doc)\
                    .OfCategory(DB.BuiltInCategory.OST_Sheets)\
                    .WhereElementIsNotElementType()\
                    .ToElements()

sheets = sorted(sheetsnotsorted, key=lambda x: x.SheetNumber)

for s in sheets:
    hasSelectedRevision = False
    revision_ids = s.GetAllRevisionIds()
    revids = [get_elementid_value(x) for x in revision_ids]
    for sr in selectedrevs:
        if sr in revids:
            hasSelectedRevision = True
    if hasSelectedRevision:
        print('{0}\t{1}'.format(s.Parameter[DB.BuiltInParameter.SHEET_NUMBER].AsString(),
                                s.Parameter[DB.BuiltInParameter.SHEET_NAME].AsString()))

        if multipleRevs:
            for revid in revision_ids:
                rev = revit.doc.GetElement(revid)
                revit.report.print_revision(rev, prefix='\t\t', print_id=False)
