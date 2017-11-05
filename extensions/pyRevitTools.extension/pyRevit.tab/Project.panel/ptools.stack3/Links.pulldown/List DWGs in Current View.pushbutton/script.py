"""Lists all linked and imported DWG instances with worksets and creator."""

import clr
from collections import defaultdict

from pyrevit import revit, DB
from pyrevit import script


output = script.get_output()


dwgs = DB.FilteredElementCollector(revit.doc)\
         .OfClass(DB.ImportInstance)\
         .WhereElementIsNotElementType()\
         .ToElements()

dwgInst = defaultdict(list)
workset_table = revit.doc.GetWorksetTable()


for dwg in dwgs:
    if dwg.IsLinked:
        dwgInst["LINKED DWGs:"].append(dwg)
    else:
        dwgInst["IMPORTED DWGs:"].append(dwg)


for link_mode in dwgInst:
    output.print_md("####{}".format(link_mode))
    for dwg in dwgInst[link_mode]:
        dwg_id = dwg.Id
        dwg_name = dwg.LookupParameter("Name").AsString()
        dwg_workset = workset_table.GetWorkset(dwg.WorksetId).Name
        dwg_instance_creator = \
            DB.WorksharingUtils.GetWorksharingTooltipInfo(revit.doc,
                                                          dwg.Id).Creator

        if revit.activeview.Id == dwg.OwnerViewId:
            output.print_md("\n**DWG name:** {}\n"
                            "DWG created by:{}\n"
                            "DWG id: {}\n"
                            "DWG workset: {}\n".format(dwg_name,
                                                       dwg_instance_creator,
                                                       output.linkify(dwg_id),
                                                       dwg_workset))
