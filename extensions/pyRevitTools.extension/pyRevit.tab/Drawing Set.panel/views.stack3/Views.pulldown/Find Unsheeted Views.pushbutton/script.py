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
all_sheeted_view_ids = set()

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
    vp_ids = [doc.GetElement(x).ViewId.IntegerValue for x in sht.GetAllViewports()]
    all_sheeted_view_ids = all_sheeted_view_ids.union(vp_ids)


this_script.output.print_md('### DRAFTING VIEWS NOT ON ANY SHEETS')
for dv in dviews:
    if dv.Id.IntegerValue in all_sheeted_view_ids:
        continue
    else:
        print('TYPE: {1}\t\tID: {2}\t\t{0}'.format(dv.ViewName,
                                                   dv.ViewType,
                                                   this_script.output.linkify(dv.Id)))


this_script.output.print_md('### MODEL VIEWS NOT ON ANY SHEETS')
for mv in mviews:
    if mv.Id.IntegerValue in all_sheeted_view_ids:
        continue
    else:
        print('TYPE: {1}\t\tID: {2}\t\t{0}'.format(mv.ViewName,
                                                   mv.ViewType,
                                                   this_script.output.linkify(mv.Id)))


this_script.output.print_md('### LEGENDS NOT ON ANY SHEETS')
for lv in lviews:
    if lv.Id.IntegerValue in all_sheeted_view_ids:
        continue
    else:
        print('TYPE: {1}\t\tID: {2}\t\t{0}'.format(lv.ViewName,
                                                   lv.ViewType,
                                                   this_script.output.linkify(lv.Id)))
