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
__contact__ = 'https://github.com/frederic-beaupere'
__credits__ = 'http://eirannejad.github.io/pyRevit/credits/'

__doc__ = 'Lists all linked and imported DWG instances with worksets and creator.'


import clr
from collections import defaultdict

from scriptutils import this_script
from revitutils import doc

clr.AddReference("RevitAPI")

# noinspection PyUnresolvedReferences
from Autodesk.Revit.DB import FilteredElementCollector as Fec
# noinspection PyUnresolvedReferences
from Autodesk.Revit.DB import ImportInstance, WorksharingUtils


dwgs = Fec(doc).OfClass(ImportInstance).WhereElementIsNotElementType().ToElements()
dwgInst = defaultdict(list)
workset_table = doc.GetWorksetTable()


this_script.output.print_md("####LINKED AND IMPORTED DWG FILES:")
this_script.output.print_md('By: [{}]({})'.format(__author__, __contact__))


for dwg in dwgs:
    if dwg.IsLinked:
        dwgInst["LINKED DWGs:"].append(dwg)
    else:
        dwgInst["IMPORTED DWGs:"].append(dwg)

for link_mode in dwgInst:
    this_script.output.print_md("####{}".format(link_mode))
    for dwg in dwgInst[link_mode]:
        dwg_id = dwg.Id
        dwg_name = dwg.LookupParameter("Name").AsString()
        dwg_workset = workset_table.GetWorkset(dwg.WorksetId).Name
        dwg_instance_creator = WorksharingUtils.GetWorksharingTooltipInfo(doc, dwg.Id).Creator

        this_script.output.print_md("\n**DWG name:** {}\n"    \
                                    "DWG created by:{}\n"     \
                                    "DWG id: {}\n"            \
                                    "DWG workset: {}\n".format(dwg_name,
                                                               dwg_instance_creator,
                                                               this_script.output.linkify(dwg_id),
                                                               dwg_workset))
