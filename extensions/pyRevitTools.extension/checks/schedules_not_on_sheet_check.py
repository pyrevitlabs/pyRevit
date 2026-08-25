# -*- coding: UTF-8 -*-
import datetime
import os

from pyrevit import coreutils
from pyrevit import revit, DB
from pyrevit import framework
from pyrevit.coreutils import applocales
from pyrevit.preflight import PreflightTestCase

_XAML = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "locale", "Checks.xaml"
)


def _t(key):
    return applocales.get_locale_string_from_xaml(_XAML, key)


def checkModel(doc, output):
    # heavily based on Views - Query view sheet placement in pyRevit

    scheduleviews = []
    all_sheeted_view_ids = []

    # Schedules need to be collected separately
    schedule_views = (
        DB.FilteredElementCollector(revit.doc)
        .OfClass(framework.get_type(DB.ViewSchedule))
        .WhereElementIsNotElementType()
        .ToElements()
    )

    for sv in schedule_views:
        scheduleviews.append(sv)

    # Now collecting all sheets and find all sheeted views
    sheets = (
        DB.FilteredElementCollector(revit.doc)
        .OfCategory(DB.BuiltInCategory.OST_Sheets)
        .WhereElementIsNotElementType()
        .ToElements()
    )

    for sht in sheets:
        vp_ids = [revit.doc.GetElement(x).ViewId for x in sht.GetAllViewports()]
        all_sheeted_view_ids.extend(vp_ids)

    # Find all sheeted schedule views and add them to the list as well
    allSheetedSchedules = (
        DB.FilteredElementCollector(revit.doc)
        .OfClass(DB.ScheduleSheetInstance)
        .ToElements()
    )

    for ss in allSheetedSchedules:
        all_sheeted_view_ids.append(ss.ScheduleId)

    output.close_others()
    output.print_md("### {}".format(_t("SchedulesNotOnSheets")))

    for v in scheduleviews:
        if v.Id in all_sheeted_view_ids:
            continue
        else:
            print(
                "{0} {1}\t\t{2} {3}\t\t{4}".format(
                    _t("TypeLabel"),
                    v.ViewType,
                    _t("IdLabel"),
                    output.linkify(v.Id),
                    revit.query.get_name(v),
                )
            )


class ModelChecker(PreflightTestCase):
    name = _t("CheckName_SchedulesNotOnSheet")
    author = "Jean-Marc Couffin"

    def startTest(self, doc, output):
        timer = coreutils.Timer()
        checkModel(doc, output)
        endtime = timer.get_time()
        endtime_hms = str(datetime.timedelta(seconds=endtime))
        endtime_hms_claim = "{} {}".format(_t("TransactionTook"), endtime_hms)
        print(endtime_hms_claim)


ModelChecker.__doc__ = _t("CheckDescription_SchedulesNotOnSheet")
