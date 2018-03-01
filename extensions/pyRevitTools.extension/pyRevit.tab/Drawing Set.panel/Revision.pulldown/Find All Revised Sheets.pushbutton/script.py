"""Lists all sheets revised under any revision."""

from pyrevit import revit, DB
from pyrevit import script

output = script.get_output()

output.print_md('**LIST OF REVISIONS:**')


revs = DB.FilteredElementCollector(revit.doc)\
         .OfCategory(DB.BuiltInCategory.OST_Revisions)\
         .WhereElementIsNotElementType()

for rev in revs:
    revit.report.print_revision(rev)

output.print_md('*****\n\n\n###REVISED SHEETS:\n')

sheetsnotsorted = DB.FilteredElementCollector(revit.doc)\
                    .OfCategory(DB.BuiltInCategory.OST_Sheets)\
                    .WhereElementIsNotElementType()\
                    .ToElements()

sheets = sorted(sheetsnotsorted, key=lambda x: x.SheetNumber)

for sht in sheets:
    srevs = set(sht.GetAllRevisionIds())
    srevs = srevs.union(set(sht.GetAdditionalRevisionIds()))
    if len(srevs) > 0:
        revit.report.print_sheet(sht)

        for rev in srevs:
            rev = revit.doc.GetElement(rev)
            revit.report.print_revision(rev, prefix='\t\t', print_id=False)
