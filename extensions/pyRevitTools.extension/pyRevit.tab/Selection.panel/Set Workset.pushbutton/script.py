"""
This tool will set the active workset from the selected element's workset.
Copyright (c) 2020 Jean-Marc Couffin
https://github.com/jmcouffin
"""

# pylint: disable=import-error,invalid-name,broad-except,superfluous-parens
from pyrevit import revit, forms, script, DB
from pyrevit.framework import List

my_config = script.get_config()

set_workset = my_config.get_option("set_workset", True)
set_workset_checkout = my_config.get_option("set_workset_checkout", False)
set_workplane_to_level = my_config.get_option("set_workplane_to_level", False)
set_phase = my_config.get_option("set_phase", False)
# set_design_option = my_config.get_option("set_design_option", False)

selection = revit.get_selection()
if selection.is_empty:
    picked = revit.pick_element()
    if picked:
        selection = [picked]
    else:
        script.exit()

element = selection[0]

if set_workset and forms.check_workshared():
    workset = revit.query.get_element_workset(element)
    if workset:
        with revit.Transaction("Set Active Workset"):
            revit.update.set_active_workset(workset.Id, doc=revit.doc)

if set_workset_checkout and forms.check_workshared():
    workset = revit.query.get_element_workset(element)
    if workset:
        workset_ids = List[DB.WorksetId]()
        workset_ids.Add(workset.Id)
        DB.WorksharingUtils.CheckoutWorksets(revit.doc, workset_ids)

if set_workplane_to_level:
    wp_param = element.get_Parameter(DB.BuiltInParameter.SCHEDULE_LEVEL_PARAM)
    if wp_param and wp_param.HasValue:
        level_id = wp_param.AsElementId()
        if level_id and level_id != DB.ElementId.InvalidElementId:
            level = revit.doc.GetElement(level_id)
            if isinstance(level, DB.Level):
                elevation = level.Elevation
                plane = DB.Plane.CreateByNormalAndOrigin(
                    DB.XYZ.BasisZ,  # Up vector
                    DB.XYZ(0, 0, elevation)
                )
                with revit.Transaction("Set Active Work Plane"):
                    sketch_plane = DB.SketchPlane.Create(revit.doc, plane)
                    revit.doc.ActiveView.SketchPlane = sketch_plane
                    revit.doc.ActiveView.ShowActiveWorkPlane()

if set_phase:
    pc_param = element.get_Parameter(DB.BuiltInParameter.PHASE_CREATED)
    if pc_param and pc_param.HasValue:
        phase_created_id = pc_param.AsElementId()
        phase = revit.doc.GetElement(phase_created_id)
        if phase:
            with revit.Transaction("Set View Phase"):
                revit.doc.ActiveView.get_Parameter(DB.BuiltInParameter.VIEW_PHASE).Set(
                    phase.Id
                )

# Not yet exposed by API
# Idea Board: https://forums.autodesk.com/t5/revit-ideas/design-options-api/idi-p/9590221
# if set_design_option:
#     do_param = element.get_Parameter(DB.BuiltInParameter.DESIGN_OPTION_ID)
#     if do_param and do_param.HasValue:
#         design_option_id = do_param.AsElementId()
#         design_option = revit.doc.GetElement(design_option_id)
#         if design_option:
#             with revit.Transaction("Set Active Design Option"):
#                 DB.DesignOption.SetActiveDesignOptionId = design_option
