# -*- coding: UTF-8 -*-
#pylint: disable=import-error,invalid-name,broad-except,superfluous-parens
import datetime

from pyrevit import coreutils
from pyrevit import script
from pyrevit import revit, DB
from pyrevit import framework

from pyrevit.preflight import PreflightTestCase
from pyrevit.compat import safe_strtype

def checkModel(doc, output):
    # heavily based on Views - Query view sheet placement in pyRevit

    scheduleviews = []
    all_sheeted_view_ids = []

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

    output.close_others()
    output.print_md('### SCHEDULES NOT ON ANY SHEETS')

    for v in scheduleviews:
        if v.Id in all_sheeted_view_ids:
            continue
        else:
            print('TYPE: {1}\t\tID: {2}\t\t{0}'.format(revit.query.get_name(v),
                                                       v.ViewType,
                                                       output.linkify(v.Id)))

class ModelChecker(PreflightTestCase):
    """
    List all schedules not placed on a sheet
    This QC tools returns you with the following data:
        Type, Id + link and Schedule name with the ability to click on the link to open the schedule

    """

    name = "Schedules not on sheet lister"
    author = "Jean-Marc Couffin"

    def setUp(self, doc, output):
        pass

    def startTest(self, doc, output):
        timer = coreutils.Timer()
        checkModel(doc, output)
        endtime = timer.get_time()
        endtime_hms = str(datetime.timedelta(seconds=endtime))
        endtime_hms_claim = "Transaction took " + endtime_hms
        print(endtime_hms_claim)

    def tearDown(self, doc, output):
        pass

    def doCleanups(self, doc, output):
        pass
