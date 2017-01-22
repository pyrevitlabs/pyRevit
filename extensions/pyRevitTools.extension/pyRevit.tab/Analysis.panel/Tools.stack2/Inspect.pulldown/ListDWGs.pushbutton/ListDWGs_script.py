"""
List DWGs
Lists all linked and imported DWG instances with worksets and creator.

Copyright (c) 2017 Frederic Beaupere
github.com/frederic-beaupere

--------------------------------------------------------
PyRevit Notice:
Copyright (c) 2014-2017 Ehsan Iran-Nejad
pyRevit: repository at https://github.com/eirannejad/pyRevit

"""

__title__ = 'List DWGs'
__author__ = 'Frederic Beaupere'
__contact__ = 'github.com/frederic-beaupere'
__credits__ = 'http://eirannejad.github.io/pyRevit/credits/'
__doc__ = """Lists all linked and imported DWG instances with worksets and creator."""

import clr
clr.AddReference("RevitAPI")
import Autodesk
from Autodesk.Revit.DB import FilteredElementCollector as fec
from Autodesk.Revit.DB import ImportInstance
from Autodesk.Revit.DB import WorksharingUtils
from revitutils import doc
from collections import defaultdict

dwgs = fec(doc).OfClass(ImportInstance).WhereElementIsNotElementType().ToElements()
dwgInst = defaultdict(list)
workset_table = doc.GetWorksetTable()

for dwg in dwgs:
    if dwg.IsLinked:
        dwgInst["LINKED:"].append(dwg)
    else:
        dwgInst["IMPORTED:"].append(dwg)

for link_mode in dwgInst:
    print("\n" + 9 * "_" + link_mode)
    for dwg in dwgInst[link_mode]:
        dwg_id = dwg.Id.ToString()
        dwg_name = dwg.LookupParameter("Name").AsString()
        dwg_workset = workset_table.GetWorkset(dwg.WorksetId).Name
        dwg_instance_creator = WorksharingUtils.GetWorksharingTooltipInfo(doc, dwg.Id).Creator

        print("DWG created by:{0} id: {1} DWG name:{2} on workset: {3}".format(
                    dwg_instance_creator.ljust(12),
                    dwg_id.rjust(9),
                    dwg_name.rjust(6),
                    dwg_workset.ljust(110)))
