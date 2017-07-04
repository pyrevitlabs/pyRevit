"""Lists views that have not been placed on any sheets."""

from scriptutils import this_script

from rpw import doc

import clr
# noinspection PyUnresolvedReferences
from Autodesk.Revit.DB import FilteredElementCollector as Fec
# noinspection PyUnresolvedReferences
from Autodesk.Revit.DB import BuiltInCategory, View, ViewType, \
                              ScheduleSheetInstance, ViewSchedule


# COLELCTING DATA --------------------------------------------------------------
dviews = []
mviews = []
lviews = []
scheduleviews = []
all_sheeted_view_ids = []

# Collecting all the model, drafting, and legend views
views = Fec(doc).OfCategory(BuiltInCategory.OST_Views)\
                .WhereElementIsNotElementType().ToElements()
for v in views:
    if not v.IsTemplate:
        if v.ViewType == ViewType.DraftingView:
            dviews.append(v)
        elif v.ViewType == ViewType.Legend:
            lviews.append(v)
        else:
            mviews.append(v)

# Schedules need to be collected separately
schedule_views = Fec(doc).OfClass(clr.GetClrType(ViewSchedule))\
                         .WhereElementIsNotElementType().ToElements()
for sv in schedule_views:
    scheduleviews.append(sv)


# Now collecting all sheets and find all sheeted views
sheets = Fec(doc).OfCategory(BuiltInCategory.OST_Sheets)\
                 .WhereElementIsNotElementType().ToElements()
for sht in sheets:
    vp_ids = [doc.GetElement(x).ViewId for x in sht.GetAllViewports()]
    all_sheeted_view_ids.extend(vp_ids)


# Find all sheeted schedule views and add them to the list as well
allSheetedSchedules = Fec(doc).OfClass(ScheduleSheetInstance).ToElements()
for ss in allSheetedSchedules:
    all_sheeted_view_ids.append (ss.ScheduleId)

# NOW LET'S REPORT -------------------------------------------------------------

out = this_script.output

out.print_md('### DRAFTING VIEWS NOT ON ANY SHEETS')
for v in dviews:
    if v.Id in all_sheeted_view_ids:
        continue
    else:
        print('TYPE: {1}\t\tID: {2}\t\t{0}'.format(v.ViewName,
                                                   v.ViewType,
                                                   out.linkify(v.Id)))


out.print_md('### MODEL VIEWS NOT ON ANY SHEETS')
for v in mviews:
    if v.Id in all_sheeted_view_ids:
        continue
    else:
        print('TYPE: {1}\t\tID: {2}\t\t{0}'.format(v.ViewName,
                                                   v.ViewType,
                                                   out.linkify(v.Id)))


out.print_md('### LEGENDS NOT ON ANY SHEETS')
for v in lviews:
    if v.Id in all_sheeted_view_ids:
        continue
    else:
        print('TYPE: {1}\t\tID: {2}\t\t{0}'.format(v.ViewName,
                                                   v.ViewType,
                                                   out.linkify(v.Id)))


out.print_md('### SCHEDULES NOT ON ANY SHEETS')
for v in scheduleviews:
    if v.Id in all_sheeted_view_ids:
        continue
    else:
        print('TYPE: {1}\t\tID: {2}\t\t{0}'.format(v.ViewName,
                                                   v.ViewType,
                                                   out.linkify(v.Id)))
