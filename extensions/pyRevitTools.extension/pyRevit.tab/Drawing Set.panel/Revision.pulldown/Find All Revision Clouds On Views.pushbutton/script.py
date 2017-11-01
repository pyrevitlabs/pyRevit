from pyrevit import revit, DB


__doc__ = 'Lists all revision clouds in this model that have been '\
          'placed on a view and not on sheet.'

revs = DB.FilteredElementCollector(revit.doc)\
         .OfCategory(DB.BuiltInCategory.OST_RevisionClouds)\
         .WhereElementIsNotElementType()

for rev in revs:
    parent = revit.doc.GetElement(rev.OwnerViewId)
    if isinstance(parent, DB.ViewSheet):
        continue
    else:
        print('REV#: {0}\t\tID: {2}\t\tON VIEW: {1}'
              .format(revit.doc.GetElement(rev.RevisionId).RevisionNumber,
                      parent.ViewName,
                      rev.Id))

print('\nSEARCH COMPLETED.')
