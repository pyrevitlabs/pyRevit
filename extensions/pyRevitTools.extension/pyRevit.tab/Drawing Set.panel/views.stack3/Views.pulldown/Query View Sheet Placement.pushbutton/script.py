"""Lists views that have not been placed on any sheets."""

from pyrevit import framework
from pyrevit import revit, DB
from pyrevit import script


out = script.get_output()


# COLELCTING DATA
dviews = []
mviews = []
lviews = []
scheduleviews = []
all_sheeted_view_ids = []

# Collecting all the model, drafting, and legend views
views = DB.FilteredElementCollector(revit.doc)\
          .OfCategory(DB.BuiltInCategory.OST_Views)\
          .WhereElementIsNotElementType()\
          .ToElements()

for v in views:
    if not v.IsTemplate:
        if v.ViewType == DB.ViewType.DraftingView:
            dviews.append(v)
        elif v.ViewType == DB.ViewType.Legend:
            lviews.append(v)
        else:
            mviews.append(v)

# Schedules need to be collected separately
schedule_views = DB.FilteredElementCollector(revit.doc)\
                   .OfClass(framework.get_type(DB.ViewSchedule))\
                   .WhereElementIsNotElementType()\
                   .ToElements()

for sv in schedule_views:
    scheduleviews.append(sv)


# Now collecting all sheets and find all sheeted views
sheets = DB.FilteredElementCollector(revit.doc)\
           .OfCategory(DB.BuiltInCategory.OST_Sheets)\
           .WhereElementIsNotElementType()\
           .ToElements()

for sht in sheets:
    vp_ids = [revit.doc.GetElement(x).ViewId for x in sht.GetAllViewports()]
    all_sheeted_view_ids.extend(vp_ids)


# Find all sheeted schedule views and add them to the list as well
allSheetedSchedules = DB.FilteredElementCollector(revit.doc)\
                        .OfClass(DB.ScheduleSheetInstance)\
                        .ToElements()

for ss in allSheetedSchedules:
    all_sheeted_view_ids.append(ss.ScheduleId)

# NOW LET'S REPORT
out.print_md('### DRAFTING VIEWS NOT ON ANY SHEETS')
for v in dviews:
    if v.Id in all_sheeted_view_ids:
        continue
    else:
        print('TYPE: {1}\t\tID: {2}\t\t{0}'.format(revit.query.get_name(v),
                                                   v.ViewType,
                                                   out.linkify(v.Id)))


out.print_md('### MODEL VIEWS NOT ON ANY SHEETS')
for v in mviews:
    if v.Id in all_sheeted_view_ids:
        continue
    else:
        print('TYPE: {1}\t\tID: {2}\t\t{0}'.format(revit.query.get_name(v),
                                                   v.ViewType,
                                                   out.linkify(v.Id)))


out.print_md('### LEGENDS NOT ON ANY SHEETS')
for v in lviews:
    if v.Id in all_sheeted_view_ids:
        continue
    else:
        print('TYPE: {1}\t\tID: {2}\t\t{0}'.format(revit.query.get_name(v),
                                                   v.ViewType,
                                                   out.linkify(v.Id)))


out.print_md('### SCHEDULES NOT ON ANY SHEETS')
for v in scheduleviews:
    if v.Id in all_sheeted_view_ids:
        continue
    else:
        print('TYPE: {1}\t\tID: {2}\t\t{0}'.format(revit.query.get_name(v),
                                                   v.ViewType,
                                                   out.linkify(v.Id)))
