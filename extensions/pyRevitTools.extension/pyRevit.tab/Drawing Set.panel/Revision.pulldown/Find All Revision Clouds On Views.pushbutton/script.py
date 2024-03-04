from pyrevit import revit, DB
from pyrevit import script
output = script.get_output()
output.close_others()

revcs = DB.FilteredElementCollector(revit.doc)\
         .OfCategory(DB.BuiltInCategory.OST_RevisionClouds)\
         .WhereElementIsNotElementType()

for revc in revcs:
    parent = revit.doc.GetElement(revc.OwnerViewId)
    if isinstance(parent, DB.ViewSheet):
        continue
    else:
        rev = revit.doc.GetElement(revc.RevisionId)
        wrev = revit.query.get_name(rev)
        rev_number = revit.query.get_param(revc, "Revision Number").AsValueString()
        rev_seq_id = revit.query.get_param(rev,
                                        'Revision Number',
                                        rev.SequenceNumber).AsValueString()
        
        rev_no = rev_number if not rev_seq_id else rev_seq_id
        rev_seq_number = rev.SequenceNumber
        selectable_cloud_id = output.linkify([revc.Id])

        print('REV#: {rev_no}\t\tREV SEQ#: {rev_seq_no}\t\tID: {cloud_id}\t\tON VIEW: {view_name}'
              .format(
                  rev_no=rev_no,
                  view_name=revit.query.get_name(parent),
                  cloud_id=selectable_cloud_id,
                  rev_seq_no =rev_seq_number))

print('\nSEARCH COMPLETED.')
