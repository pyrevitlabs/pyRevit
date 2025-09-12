"""
This tool will set the active workset from the selected element's workset.
"""

# pylint: disable=import-error,invalid-name,broad-except,superfluous-parens
from pyrevit import revit, forms, script, DB
from pyrevit.framework import List

my_config = script.get_config()

set_workset = my_config.get_option("set_workset", True)
set_workset_checkout = my_config.get_option("set_workset_checkout", False)
set_workplane_to_level = my_config.get_option("set_workplane_to_level", False)
set_workplane_visible = my_config.get_option("set_workplane_visible", False)
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
    level = None
    level_name = None

    # Try parameters in order
    param_order = [
        DB.BuiltInParameter.SKETCH_PLANE_PARAM,
        DB.BuiltInParameter.SCHEDULE_LEVEL_PARAM,
        DB.BuiltInParameter.LEVEL_PARAM,
    ]

    for bip in param_order:
        level_param = element.get_Parameter(bip)
        if level_param and level_param.HasValue:
            if bip == DB.BuiltInParameter.SKETCH_PLANE_PARAM:
                raw = level_param.AsValueString()
                if raw:
                    level_name = raw.split(":")[-1].strip()
            else:
                level_name = level_param.AsValueString()

            if level_name:
                levels = {
                    lvl.Name: lvl
                    for lvl in DB.FilteredElementCollector(revit.doc).OfClass(DB.Level)
                }
                level = levels.get(level_name)
            break

    if not level and hasattr(element, "LevelId"):
        level_id = element.LevelId
        if level_id and level_id != DB.ElementId.InvalidElementId:
            level = revit.doc.GetElement(level_id)

    if level:
        with revit.Transaction("Set Active Work Plane to Level"):
            sketch_plane = DB.SketchPlane.Create(revit.doc, level.Id)
            revit.doc.ActiveView.SketchPlane = sketch_plane
            if set_workplane_visible:
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
