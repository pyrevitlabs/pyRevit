"""Lists all sheets revised under any revision."""

from revitutils import doc
from scriptutils import this_script
from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory

this_script.output.print_md('**LIST OF REVISIONS:**')
cl = FilteredElementCollector(doc)
revs = cl.OfCategory(BuiltInCategory.OST_Revisions).WhereElementIsNotElementType()
for rev in revs:
    print('{0}\tREV#: {1}\tDATE: {2}\tTYPE:{3}\tDESC: {4}'.format(rev.SequenceNumber,
                                                                  str(rev.RevisionNumber).ljust(5),
                                                                  str(rev.RevisionDate).ljust(10),
                                                                  str(rev.NumberType.ToString()).ljust(15),
                                                                  rev.Description))

this_script.output.print_md('*****\n\n\n###REVISED SHEETS:\n')

sheetsnotsorted = FilteredElementCollector(doc).OfCategory(
    BuiltInCategory.OST_Sheets).WhereElementIsNotElementType().ToElements()
sheets = sorted(sheetsnotsorted, key=lambda x: x.SheetNumber)

for sht in sheets:
    revs = sht.GetAllRevisionIds()
    if len(revs) > 0:
        print('{}\t{}\t{}'.format(this_script.output.linkify(sht.Id),
                                  sht.LookupParameter('Sheet Number').AsString(),
                                  sht.LookupParameter('Sheet Name').AsString()))
        for rev in revs:
            rev = doc.GetElement(rev)
            print('\tREV#: {0}\t\tDATE: {1}\t\tDESC:{2}'.format(rev.RevisionNumber,
                                                                rev.RevisionDate,
                                                                rev.Description
                                                                ))
