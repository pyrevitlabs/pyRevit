"""Sets the revision visibility parameter to None for all revisions."""

from pyrevit import revit, DB

revs = DB.FilteredElementCollector(revit.doc)\
         .OfCategory(DB.BuiltInCategory.OST_Revisions)\
         .WhereElementIsNotElementType()

with revit.Transaction('Turn off Revisions'):
    for rev in revs:
        rev.Visibility = DB.RevisionVisibility.Hidden
