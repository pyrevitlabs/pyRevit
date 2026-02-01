# -*- coding: UTF-8 -*-
import datetime

from pyrevit import coreutils
from pyrevit import script
from pyrevit import revit, DB
from pyrevit import framework

import sys
import os
# Add current directory to path for local imports
_current_dir = os.path.dirname(os.path.abspath(__file__))
if _current_dir not in sys.path:
    sys.path.insert(0, _current_dir)

from pyrevit.preflight import PreflightTestCase
from pyrevit.compat import safe_strtype
from check_translations import DocstringMeta

def checkModel(doc, output):
    from check_translations import get_check_translation
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
    output.print_md('### {}'.format(get_check_translation("SchedulesNotOnSheets")))

    for v in scheduleviews:
        if v.Id in all_sheeted_view_ids:
            continue
        else:
            print('{0} {1}\t\t{2} {3}\t\t{4}'.format(
                get_check_translation("TypeLabel"),
                v.ViewType,
                get_check_translation("IdLabel"),
                output.linkify(v.Id),
                revit.query.get_name(v)))

class ModelChecker(PreflightTestCase):
    __metaclass__ = DocstringMeta
    _docstring_key = "CheckDescription_SchedulesNotOnSheet"
    
    @property
    def name(self):
        from check_translations import get_check_translation
        return get_check_translation("CheckName_SchedulesNotOnSheet")
    
    author = "Jean-Marc Couffin"


    def startTest(self, doc, output):
        timer = coreutils.Timer()
        checkModel(doc, output)
        endtime = timer.get_time()
        endtime_hms = str(datetime.timedelta(seconds=endtime))
        from check_translations import get_check_translation
        endtime_hms_claim = "{} {}".format(get_check_translation("TransactionTook"), endtime_hms)
        print(endtime_hms_claim)
