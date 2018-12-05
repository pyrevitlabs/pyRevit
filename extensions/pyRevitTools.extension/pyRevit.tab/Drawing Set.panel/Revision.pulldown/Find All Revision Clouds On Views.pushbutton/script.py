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
        wrev = revit.ElementWrapper(rev)
        print('REV#: {0}\t\tID: {2}\t\tON VIEW: {1}'
              .format(wrev.safe_get_param('RevisionNumber',
                                          rev.SequenceNumber),
                      parent.ViewName,
                      revc.Id))

print('\nSEARCH COMPLETED.')
