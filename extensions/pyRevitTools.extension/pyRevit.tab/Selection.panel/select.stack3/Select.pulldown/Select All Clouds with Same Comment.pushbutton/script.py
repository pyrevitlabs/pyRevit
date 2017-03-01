"""Selects all revision clouds in the model with comment matching selected revision cloud."""

from revitutils import doc, uidoc, selection

# noinspection PyUnresolvedReferences
from System.Collections.Generic import List
# noinspection PyUnresolvedReferences
from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory, ElementId, RevisionCloud
# noinspection PyUnresolvedReferences
from Autodesk.Revit.UI import TaskDialog


# collect all revision clouds
cl = FilteredElementCollector(doc)
revclouds = cl.OfCategory(BuiltInCategory.OST_RevisionClouds).WhereElementIsNotElementType()


# get selected revision cloud info
src_comment = None
for el in selection.elements:
    if isinstance(el, RevisionCloud):
        src_comment = el.LookupParameter('Comments').AsString()

# find matching clouds
if src_comment:
    clouds = []
    for revcloud in revclouds:
        dest_comment = revcloud.LookupParameter('Comments').AsString()
        if src_comment == dest_comment:
            clouds.append(revcloud.Id)

    # Replace revit selection with matched clouds
    uidoc.Selection.SetElementIds(List[ElementId](clouds))
else:
    TaskDialog.Show('pyRevit', 'At least one Revision Cloud must be selected.')
