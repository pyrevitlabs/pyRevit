# -*- coding: UTF-8 -*-
from pyrevit import revit, DB
from pyrevit import script
from pyrevit import forms

logger = script.get_logger()

my_config = script.get_config()

set_type_ws = my_config.get_option("set_type_ws", False)
set_all = my_config.get_option("set_all", False)
custom_prefix_for_rvt = my_config.get_option("custom_prefix_for_rvt", False)
custom_prefix_for_dwg = my_config.get_option("custom_prefix_for_dwg", False)

if not set_all:
    selection = revit.get_selection()
else:
    selection = (
        DB.FilteredElementCollector(revit.doc)
        .WhereElementIsNotElementType()
        .WherePasses(DB.LogicalOrFilter([
            DB.ElementClassFilter(DB.RevitLinkInstance),
            DB.ElementClassFilter(DB.ImportInstance)
        ]))
        .ToElements()
    )

if len(selection) > 0:
    for el in selection:
        linked_model_name = ""
        if isinstance(el, DB.RevitLinkInstance):
            prefix_for_rvt_value = "ZL_RVT_"
            if custom_prefix_for_rvt:
                prefix_for_rvt_value = my_config.get_option(
                    "custom_prefix_rvt_value", prefix_for_rvt_value
                )
            linked_model_name = (
                prefix_for_rvt_value + el.Name.split(":")[0].split(".rvt")[0]
            )
        elif isinstance(el, DB.ImportInstance):
            prefix_for_dwg_value = "ZL_DWG_"
            if custom_prefix_for_dwg:
                prefix_for_dwg_value = my_config.get_option(
                    "custom_prefix_dwg_value", prefix_for_dwg_value
                )
            linked_model_name = (
                prefix_for_dwg_value
                + el.get_Parameter(DB.BuiltInParameter.IMPORT_SYMBOL_NAME)
                .AsString()
                .split(".dwg")[0]
            )
        if linked_model_name:
            with revit.Transaction("Create Workset for linked model"):
                if not revit.doc.IsWorkshared and revit.doc.CanEnableWorksharing:
                    revit.doc.EnableWorksharing("Shared Levels and Grids", "Workset1")
                try:
                    user_worksets = (
                        DB.FilteredWorksetCollector(revit.doc)
                        .OfKind(DB.WorksetKind.UserWorkset)
                        .ToWorksets()
                    )
                    existing_ws = None
                    for ws in user_worksets:
                        if ws.Name == linked_model_name:
                            existing_ws = ws
                            break
                    if existing_ws:
                        workset = existing_ws
                    else:
                        workset = DB.Workset.Create(revit.doc, linked_model_name)
                    worksetParam = el.get_Parameter(
                        DB.BuiltInParameter.ELEM_PARTITION_PARAM
                    )
                    success = False
                    if not worksetParam.IsReadOnly:
                        worksetParam.Set(workset.Id.IntegerValue)
                        success = True
                    else:
                        logger.error("Instance Workset Parameter is read-only")
                    if set_type_ws:
                        type_id = el.GetTypeId()
                        type_el = revit.doc.GetElement(type_id)
                        type_workset_param = type_el.get_Parameter(
                            DB.BuiltInParameter.ELEM_PARTITION_PARAM
                        )
                        if not type_workset_param.IsReadOnly:
                            type_workset_param.Set(workset.Id.IntegerValue)
                            success = True
                        else:
                            logger.error("Type Workset Parameter is read-only")
                    if not success and not existing_ws:
                        workset_table = revit.doc.GetWorksetTable()
                        workset_table.DeleteWorkset(
                            revit.doc, workset.Id, DB.DeleteWorksetSettings()
                        )
                except Exception as e:
                    logger.error(
                        "Error setting Workset for: {}\nError: {}".format(
                            linked_model_name, e
                        )
                    )
else:
    forms.alert("At least one linked element must be selected.")
