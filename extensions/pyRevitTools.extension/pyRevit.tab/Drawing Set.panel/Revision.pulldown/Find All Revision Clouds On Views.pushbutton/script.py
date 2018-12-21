from pyrevit import revit, DB


__doc__ = 'Lists all revision clouds in this model that have been '\
          'placed on a view and not on sheet.'

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
        print('REV#: {0}\t\tID: {2}\t\tON VIEW: {1}'
              .format(
                  revit.query.get_param(rev,
                                        'RevisionNumber',
                                        rev.SequenceNumber),
                  revit.query.get_name(parent),
                  revc.Id))

print('\nSEARCH COMPLETED.')
