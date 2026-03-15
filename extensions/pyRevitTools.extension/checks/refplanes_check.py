# -*- coding: UTF-8 -*-
import datetime

from pyrevit import coreutils
from pyrevit import script
from pyrevit import revit, DB

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
    
    output.print_md("### {0}<br />".format(get_check_translation("ReferencePlanes")))
    # reference plane without name
    refPlaneCollector = (
        DB.FilteredElementCollector(doc)
        .OfClass(DB.ReferencePlane)
        .ToElements()
    )
    RefPCount = len(refPlaneCollector)
    output.print_md("\n**{0} **{1} \n\n".format(get_check_translation("ReferencePlanesCount"), RefPCount))
    noNameRefPCount = 0
    
    refPlaneList, refPlanNames = [], []

    for refPlane in refPlaneCollector:
        refPlaneList.append(refPlane.Id)
        refPlanNames.append(refPlane.Name)
        output.print_md("{0} {1}\t\t{2} {3}"
                        .format(get_check_translation("NameLabel"), refPlane.Name,
                                get_check_translation("IdLabel"), output.linkify(refPlane.Id)))

class ModelChecker(PreflightTestCase):
    __metaclass__ = DocstringMeta
    _docstring_key = "CheckDescription_ReferencePlanLister"
    
    @property
    def name(self):
        from check_translations import get_check_translation
        return get_check_translation("CheckName_ReferencePlanLister")
    
    author = "Jean-Marc Couffin"


    def startTest(self, doc, output):
        timer = coreutils.Timer()
        checkModel(doc, output)
        endtime = timer.get_time()
        endtime_hms = str(datetime.timedelta(seconds=endtime))
        from check_translations import get_check_translation
        endtime_hms_claim = "{} {}".format(get_check_translation("TransactionTook"), endtime_hms)
        print(endtime_hms_claim)
