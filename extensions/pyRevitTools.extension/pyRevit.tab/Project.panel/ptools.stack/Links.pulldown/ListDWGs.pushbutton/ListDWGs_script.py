# -*- coding: UTF-8 -*-
"""Lists all linked and imported DWG instances with worksets and creator."""
from collections import defaultdict

from pyrevit import revit, DB
from pyrevit import script
from pyrevit import forms


output = script.get_output()
mlogger = script.get_logger()


def listdwgs(current_view_only=False):
    dwgs = (
        DB.FilteredElementCollector(revit.doc)
        .OfClass(DB.ImportInstance)
        .WhereElementIsNotElementType()
        .ToElements()
    )

    dwgInst = defaultdict(list)

    output.print_md("## LINKED AND IMPORTED DWG FILES:")
    output.print_md(
        "By: [{}]({})".format(
            "Frederic Beaupere", "https://github.com/frederic-beaupere"
        )
    )

    for dwg in dwgs:
        if dwg.IsLinked:
            dwgInst["LINKED DWGs:"].append(dwg)
        else:
            dwgInst["IMPORTED DWGs:"].append(dwg)

    for link_mode in dwgInst:
        output.print_md("####{}".format(link_mode))
        for dwg in dwgInst[link_mode]:
            dwg_id = dwg.Id
            dwg_name = dwg.Parameter[DB.BuiltInParameter.IMPORT_SYMBOL_NAME].AsString()
            dwg_workset = revit.query.get_element_workset(dwg).Name
            dwg_instance_creator = DB.WorksharingUtils.GetWorksharingTooltipInfo(
                revit.doc, dwg.Id
            ).Creator

            if current_view_only and revit.active_view.Id != dwg.OwnerViewId:
                continue

            # Get hosted level name
            level = revit.doc.GetElement(dwg.LevelId)
            level_name = level.Name if level else "N/A"

            # Get offset using the Transform
            offset_z = "N/A"
            offset_z_m = "N/A"
            try:
                transform = dwg.GetTransform()
                if transform:
                    offset_z = transform.Origin.Z  # in feet
                    offset_z_m = DB.UnitUtils.ConvertFromInternalUnits(
                        offset_z, DB.UnitTypeId.Meters
                    )
            except Exception as ex:
                mlogger.debug(
                    "Failed to convert offset Z from internal units: {}".format(ex)
                )

            print("\n\n")
            output.print_md(
                "**DWG name:** {}\n\n"
                "- DWG created by: {}\n\n"
                "- DWG id: {}\n\n"
                "- DWG workset: {}\n\n"
                "- Hosted level: {}\n\n"
                "- Offset from level (Z): {} ft ({} m)\n\n".format(
                    dwg_name,
                    dwg_instance_creator,
                    output.linkify(dwg_id),
                    dwg_workset,
                    level_name,
                    offset_z,
                    offset_z_m,
                )
            )


selected_option = forms.CommandSwitchWindow.show(
    ["In Current View", "In Model"], message="Select search option:"
)

if selected_option:
    listdwgs(current_view_only=selected_option == "In Current View")
