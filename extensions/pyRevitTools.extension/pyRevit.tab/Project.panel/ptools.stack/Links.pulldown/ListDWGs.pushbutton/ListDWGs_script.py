# -*- coding: UTF-8 -*-
"""Lists all linked and imported DWG instances with worksets and creator."""
import clr
from collections import defaultdict

from pyrevit import revit, DB
from pyrevit import script
from pyrevit import forms


output = script.get_output()
output.close_others()

def listdwgs(current_view_only=False):
    msg_imported = ":angry_face: DWG importé (au lieu de lié)"
    msg_linked = ":link: DWG lié (non importé)"
    msg_single_view = ":angry_face: DWG appartient à une seule vue (non pas au modèle)"
    dwgs = DB.FilteredElementCollector(revit.doc)\
             .OfClass(DB.ImportInstance)\
             .WhereElementIsNotElementType()\
             .ToElements()

    dwgInst = defaultdict(list)

    output.print_md("## LINKED AND IMPORTED DWG FILES:")
    output.print_md('By: [{}]({})'.format('Frederic Beaupere', 'https://github.com/frederic-beaupere'))

#    for dwg in dwgs:
#        if dwg.IsLinked:
#            dwgInst["LINKED DWGs:"].append(dwg)
#        else:
#            dwgInst["IMPORTED DWGs:"].append(dwg)

#    for link_mode in dwgInst:
#        output.print_md("####{}".format(link_mode))

    for ii, dwg in enumerate(dwgs):
        dwg_id = dwg.Id
        dwg_name = dwg.Parameter[DB.BuiltInParameter.IMPORT_SYMBOL_NAME].AsString()
        dwg_workset = revit.query.get_element_workset(dwg).Name
        dwg_instance_creator = DB.WorksharingUtils.GetWorksharingTooltipInfo(revit.doc, dwg.Id).Creator

        if current_view_only \
                and revit.active_view.Id != dwg.OwnerViewId:
            continue

        insert_msg = msg_linked if dwg.IsLinked else msg_imported
        inval = DB.ElementId.InvalidElementId
        view_msg = "" if dwg.OwnerViewId == inval else msg_single_view
        # if dwg.OwnerViewId == inval: # then the DWG belongs to one view only
        print('\n\n')
        print("{} {} {}".format(output.linkify(dwg_id, title="{}. {}".format(ii+1, dwg_name)), insert_msg, view_msg))
        print("   created by:{}. Workset: {}".format(dwg_instance_creator, dwg_workset))


selected_option = \
    forms.CommandSwitchWindow.show(
        ['ONLY in SINGLE current view',
         'In Model'],
        message='Select search options:'
        )

if selected_option:
    listdwgs(current_view_only=selected_option == 'ONLY in SINGLE current view')
