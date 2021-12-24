from pyrevit.framework import List
from pyrevit import revit, DB, UI
from pyrevit import forms


selection = revit.get_selection()


# collect all revision clouds
cl = DB.FilteredElementCollector(revit.doc)
revclouds = cl.OfCategory(DB.BuiltInCategory.OST_RevisionClouds)\
              .WhereElementIsNotElementType()


# get selected revision cloud info
src_comment = None
for el in selection.elements:
    if isinstance(el, DB.RevisionCloud):
        cparam = el.Parameter[DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS]
        src_comment = cparam.AsString()

# find matching clouds
if src_comment:
    clouds = []
    for revcloud in revclouds:
        cparam = revcloud.Parameter[DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS]
        dest_comment = cparam.AsString()
        if src_comment == dest_comment:
            clouds.append(revcloud.Id)

    # Replace revit selection with matched clouds
    revit.get_selection().set_to(clouds)
else:
    forms.alert('At least one Revision Cloud must be selected.')
