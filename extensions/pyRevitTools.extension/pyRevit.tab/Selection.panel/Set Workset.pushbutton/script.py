# -*- coding: utf-8 -*-
"""Set the active workset, work plane and view phase from the selected element."""

from pyrevit import forms, script
from pyrevit import revit, DB
from pyrevit.coreutils import applocales
from pyrevit.framework import List

logger = script.get_logger()
my_config = script.get_config()

RESOURCES = script.get_bundle_file("resources.xaml")
LEVEL_PARAMETERS = [
    DB.BuiltInParameter.SKETCH_PLANE_PARAM,
    DB.BuiltInParameter.SCHEDULE_LEVEL_PARAM,
    DB.BuiltInParameter.LEVEL_PARAM,
]


def _t(key):
    return applocales.get_locale_string_from_xaml(RESOURCES, key)


def get_source_element():
    selection = revit.get_selection()
    if selection.is_empty:
        return revit.pick_element()
    return selection.first


def set_active_workset_of(element):
    workset = revit.query.get_element_workset(element)
    if workset:
        with revit.Transaction(_t("transaction_set_workset")):
            revit.update.set_active_workset(workset.Id, doc=revit.doc)


def check_out_workset_of(element):
    workset = revit.query.get_element_workset(element)
    if workset:
        workset_ids = List[DB.WorksetId]()
        workset_ids.Add(workset.Id)
        DB.WorksharingUtils.CheckoutWorksets(revit.doc, workset_ids)


def read_level_name(element):
    # Try parameters in order
    for parameter_id in LEVEL_PARAMETERS:
        level_param = element.get_Parameter(parameter_id)
        if not (level_param and level_param.HasValue):
            continue
        if parameter_id == DB.BuiltInParameter.SKETCH_PLANE_PARAM:
            raw = level_param.AsValueString()
            return raw.split(":")[-1].strip() if raw else None
        return level_param.AsValueString()
    return None


def find_level_of(element):
    level_name = read_level_name(element)
    if level_name:
        levels = {
            level.Name: level for level in revit.query.get_elements_by_class(DB.Level)
        }
        level = levels.get(level_name)
        if level:
            return level
    level_id = getattr(element, "LevelId", None)
    if level_id and level_id != DB.ElementId.InvalidElementId:
        return revit.doc.GetElement(level_id)
    return None


def set_work_plane_to_level_of(element, show_work_plane):
    level = find_level_of(element)
    if not level:
        return
    with revit.Transaction(_t("transaction_set_work_plane")):
        sketch_plane = DB.SketchPlane.Create(revit.doc, level.Id)
        revit.doc.ActiveView.SketchPlane = sketch_plane
        if show_work_plane:
            revit.doc.ActiveView.ShowActiveWorkPlane()


def set_view_phase_of(element):
    view_phase = revit.doc.ActiveView.get_Parameter(DB.BuiltInParameter.VIEW_PHASE)
    if not view_phase or view_phase.IsReadOnly:
        logger.warning(_t("phase_not_editable"))
        return
    phase_created = element.get_Parameter(DB.BuiltInParameter.PHASE_CREATED)
    if phase_created and phase_created.HasValue:
        phase = revit.doc.GetElement(phase_created.AsElementId())
        if phase:
            with revit.Transaction(_t("transaction_set_phase")):
                view_phase.Set(phase.Id)


def main():
    set_workset = my_config.get_option("set_workset", True)
    set_workset_checkout = my_config.get_option("set_workset_checkout", False)
    set_workplane_to_level = my_config.get_option("set_workplane_to_level", False)
    set_workplane_visible = my_config.get_option("set_workplane_visible", False)
    set_phase = my_config.get_option("set_phase", False)
    # set_design_option = my_config.get_option("set_design_option", False)

    element = get_source_element()
    if not element:
        script.exit()

    if (set_workset or set_workset_checkout) and forms.check_workshared(
        message=_t("not_workshared")
    ):
        if set_workset:
            set_active_workset_of(element)
        if set_workset_checkout:
            check_out_workset_of(element)

    if set_workplane_to_level:
        set_work_plane_to_level_of(element, set_workplane_visible)

    if set_phase:
        set_view_phase_of(element)

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


if __name__ == "__main__":
    main()
