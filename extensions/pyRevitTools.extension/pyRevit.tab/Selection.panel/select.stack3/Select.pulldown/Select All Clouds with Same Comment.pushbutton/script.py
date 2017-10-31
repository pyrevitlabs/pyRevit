"""Selects all revision clouds in the model with comment matching selected revision cloud."""

from pyrevit.framework import List
from pyrevit import revit, DB, UI


selection = revit.get_selection()

# collect all revision clouds
cl = DB.FilteredElementCollector(revit.doc)
revclouds = cl.OfCategory(DB.BuiltInCategory.OST_RevisionClouds)\
              .WhereElementIsNotElementType()


# get selected revision cloud info
src_comment = None
for el in selection.elements:
    if isinstance(el, DB.RevisionCloud):
        src_comment = el.LookupParameter('Comments').AsString()

# find matching clouds
if src_comment:
    clouds = []
    for revcloud in revclouds:
        dest_comment = revcloud.LookupParameter('Comments').AsString()
        if src_comment == dest_comment:
            clouds.append(revcloud.Id)

    # Replace revit selection with matched clouds
    revit.uidoc.Selection.SetElementIds(List[DB.ElementId](clouds))
else:
    UI.TaskDialog.Show('pyRevit',
                       'At least one Revision Cloud must be selected.')
