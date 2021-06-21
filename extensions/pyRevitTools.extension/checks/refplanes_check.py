# -*- coding: UTF-8 -*-
#pylint: disable=import-error,invalid-name,broad-except,superfluous-parens
import datetime

from pyrevit import coreutils
from pyrevit import script
from pyrevit import revit, DB

from pyrevit.preflight import PreflightTestCase
from pyrevit.compat import safe_strtype

def checkModel(doc, output):

    output.print_md("### Reference planes<br />")
    # reference plane without name
    refPlaneCollector = (
        DB.FilteredElementCollector(doc)
        .OfClass(DB.ReferencePlane)
        .ToElements()
    )
    RefPCount = len(refPlaneCollector)
    output.print_md("\n**Reference planes: **{0} \n\n".format(RefPCount))
    noNameRefPCount = 0
    
    refPlaneList, refPlanNames = [], []

    for refPlane in refPlaneCollector:
        refPlaneList.append(refPlane.Id)
        refPlanNames.append(refPlane.Name)
        output.print_md("NAME: {0}\t\tID: {1}"
                        .format(refPlane.Name, output.linkify(refPlane.Id)))

class ModelChecker(PreflightTestCase):
    """
    List all reference planes in the model
    This QC tools returns you with the following data:
        Reference planes count, link to, name

    """

    name = "Reference Plan Lister"
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
