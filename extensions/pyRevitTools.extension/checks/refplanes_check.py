# -*- coding: UTF-8 -*-
import datetime
import os

from pyrevit import coreutils
from pyrevit import DB
from pyrevit.coreutils import applocales
from pyrevit.preflight import PreflightTestCase

_XAML = os.path.join(os.path.dirname(os.path.abspath(__file__)), "locale", "Checks.xaml")


def _t(key):
    return applocales.get_locale_string_from_xaml(_XAML, key)


def checkModel(doc, output):
    output.print_md("### {0}<br />".format(_t("ReferencePlanes")))
    # reference plane without name
    refPlaneCollector = (
        DB.FilteredElementCollector(doc)
        .OfClass(DB.ReferencePlane)
        .ToElements()
    )
    RefPCount = len(refPlaneCollector)
    output.print_md("\n**{0} **{1} \n\n".format(_t("ReferencePlanesCount"), RefPCount))
    noNameRefPCount = 0

    refPlaneList, refPlanNames = [], []

    for refPlane in refPlaneCollector:
        refPlaneList.append(refPlane.Id)
        refPlanNames.append(refPlane.Name)
        output.print_md("{0} {1}\t\t{2} {3}"
                        .format(_t("NameLabel"), refPlane.Name,
                                _t("IdLabel"), output.linkify(refPlane.Id)))


class ModelChecker(PreflightTestCase):
    name = _t("CheckName_ReferencePlanLister")
    author = "Jean-Marc Couffin"

    def startTest(self, doc, output):
        timer = coreutils.Timer()
        checkModel(doc, output)
        endtime = timer.get_time()
        endtime_hms = str(datetime.timedelta(seconds=endtime))
        endtime_hms_claim = "{} {}".format(_t("TransactionTook"), endtime_hms)
        print(endtime_hms_claim)


ModelChecker.__doc__ = _t("CheckDescription_ReferencePlanLister")
