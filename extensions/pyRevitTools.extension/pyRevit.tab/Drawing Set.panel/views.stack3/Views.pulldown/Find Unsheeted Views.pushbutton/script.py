"""Lists views that have not been placed on any sheets."""

from scriptutils import this_script
from revitutils import doc, uidoc

# noinspection PyUnresolvedReferences
from Autodesk.Revit.DB import FilteredElementCollector as Fec
# noinspection PyUnresolvedReferences
from Autodesk.Revit.DB import BuiltInCategory, View, ViewType


dviews = []
mviews = []
lviews = []
all_sheeted_view_ids = []

views = Fec(doc).OfCategory(BuiltInCategory.OST_Views).WhereElementIsNotElementType().ToElements()
for v in views:
    if not v.IsTemplate:
        if v.ViewType == ViewType.DraftingView:
            dviews.append(v)
        elif v.ViewType == ViewType.Legend:
            lviews.append(v)
        else:
            mviews.append(v)

sheets = Fec(doc).OfCategory(BuiltInCategory.OST_Sheets).WhereElementIsNotElementType().ToElements()
for sht in sheets:
    vp_ids = [doc.GetElement(x).ViewId for x in sht.GetAllViewports()]
    all_sheeted_view_ids.extend(vp_ids)


this_script.output.print_md('### DRAFTING VIEWS NOT ON ANY SHEETS')
for v in dviews:
    if v.Id in all_sheeted_view_ids:
        continue
    else:
        print('TYPE: {1}\t\tID: {2}\t\t{0}'.format(v.ViewName,
                                                   v.ViewType,
                                                   this_script.output.linkify(v.Id)))


this_script.output.print_md('### MODEL VIEWS NOT ON ANY SHEETS')
for v in mviews:
    if v.Id in all_sheeted_view_ids:
        continue
    else:
        print('TYPE: {1}\t\tID: {2}\t\t{0}'.format(v.ViewName,
                                                   v.ViewType,
                                                   this_script.output.linkify(v.Id)))


this_script.output.print_md('### LEGENDS NOT ON ANY SHEETS')
for v in lviews:
    if v.Id in all_sheeted_view_ids:
        continue
    else:
        print('TYPE: {1}\t\tID: {2}\t\t{0}'.format(v.ViewName,
                                                   v.ViewType,
                                                   this_script.output.linkify(v.Id)))
