"""Lists all linked and imported DWG instances with worksets and creator."""

import clr
from collections import defaultdict

from scriptutils import print_md, this_script
from revitutils import doc, uidoc

clr.AddReference("RevitAPI")

# noinspection PyUnresolvedReferences
from Autodesk.Revit.DB import FilteredElementCollector as Fec
# noinspection PyUnresolvedReferences
from Autodesk.Revit.DB import ImportInstance, WorksharingUtils


dwgs = Fec(doc).OfClass(ImportInstance).WhereElementIsNotElementType().ToElements()
dwgInst = defaultdict(list)
workset_table = doc.GetWorksetTable()


for dwg in dwgs:
    if dwg.IsLinked:
        dwgInst["LINKED DWGs:"].append(dwg)
    else:
        dwgInst["IMPORTED DWGs:"].append(dwg)

cview =uidoc.ActiveGraphicalView

for link_mode in dwgInst:
    print_md("####{}".format(link_mode))
    for dwg in dwgInst[link_mode]:
        dwg_id = dwg.Id
        dwg_name = dwg.LookupParameter("Name").AsString()
        dwg_workset = workset_table.GetWorkset(dwg.WorksetId).Name
        dwg_instance_creator = WorksharingUtils.GetWorksharingTooltipInfo(doc, dwg.Id).Creator

        if cview.Id == dwg.OwnerViewId:
            print_md("\n**DWG name:** {}\n"    \
                     "DWG created by:{}\n"     \
                     "DWG id: {}\n"            \
                     "DWG workset: {}\n".format(dwg_name,
                                                dwg_instance_creator,
                                                this_script.output.linkify(dwg_id),
                                                dwg_workset))
