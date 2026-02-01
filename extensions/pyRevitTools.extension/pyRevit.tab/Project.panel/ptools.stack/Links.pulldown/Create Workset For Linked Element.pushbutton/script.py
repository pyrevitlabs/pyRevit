# -*- coding: UTF-8 -*-
import io
import json
import os
from pyrevit import revit, DB
from pyrevit import script
from pyrevit.forms import alert
from pyrevit.userconfig import user_config
from pyrevit import HOST_APP


def get_translations(script_folder, script_type, locale):
    # type: (str, str, str) -> dict[str, str | list]
    """
    Get translation for a specific script type from a JSON file.

    Examples:
    ```python
    get_translations(script.get_script_path(), "script", "en_us")
    ```

    Args:
        script_folder (str): The folder containing the JSON file.
        script_type (str): The type of script for which translations are loaded.
            - "script"
            - "config"
        locale (str): The locale for which translations are loaded ("en_us" etc.).

    Returns:
        dict[str, str | list]: A dictionary containing the translation.
    """
    json_path = os.path.join(script_folder, 'translations.json')
    with io.open(json_path, 'r', encoding='utf-8') as f:
        translations = json.load(f)
    script_translations = translations.get(script_type, {})
    return script_translations.get(locale, script_translations.get("en_us", {}))


doc = HOST_APP.doc
logger = script.get_logger()
translations_dict = get_translations(
    script.get_script_path(),
    "script",
    user_config.user_locale
)


def main():
    """Main function to create worksets for linked elements."""
    my_config = script.get_config()

    set_type_ws = my_config.get_option("set_type_ws", False)
    set_all = my_config.get_option("set_all", False)
    custom_prefix_for_rvt = my_config.get_option("custom_prefix_for_rvt", False)
    custom_prefix_for_dwg = my_config.get_option("custom_prefix_for_dwg", False)

    if not set_all:
        selection = revit.get_selection()
    else:
        selection = (
            DB.FilteredElementCollector(doc)
            .WhereElementIsNotElementType()
            .WherePasses(DB.LogicalOrFilter([
                DB.ElementClassFilter(DB.RevitLinkInstance),
                DB.ElementClassFilter(DB.ImportInstance)
            ]))
            .ToElements()
        )

    if len(selection) > 0:
        enable_worksharing = alert(
            translations_dict["Worksharing.Enable.Message"],
            options=translations_dict["Worksharing.Enable.Options"],
            warn_icon=False
        )  # type: str
        if not enable_worksharing:
            script.exit()
        if (
            enable_worksharing == translations_dict["Worksharing.Enable.Options"][0]
            and not doc.IsWorkshared
            and doc.CanEnableWorksharing
        ):
            doc.EnableWorksharing("Shared Levels and Grids", "Workset1")
        else:
            alert(
                translations_dict["Worksharing.Enable.Error"],
                title=translations_dict["Worksharing.Enable.Error.Title"],
                exitscript=True
            )
        
        with revit.Transaction(translations_dict["Transaction.Name"]):
            for el in selection:
                linked_model_name = ""
                if isinstance(el, DB.RevitLinkInstance):
                    prefix_for_rvt_value = "RVT_"
                    if custom_prefix_for_rvt:
                        prefix_for_rvt_value = my_config.get_option(
                            "custom_prefix_rvt_value", prefix_for_rvt_value
                        )
                    linked_model_name = (
                        prefix_for_rvt_value + el.Name.split(":")[0].split(".rvt")[0]
                    )
                elif isinstance(el, DB.ImportInstance):
                    prefix_for_dwg_value = "DWG_"
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
                    try:
                        user_worksets = (
                            DB.FilteredWorksetCollector(doc)
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
                            workset = DB.Workset.Create(doc, linked_model_name)
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
                            type_el = doc.GetElement(type_id)
                            type_workset_param = type_el.get_Parameter(
                                DB.BuiltInParameter.ELEM_PARTITION_PARAM
                            )
                            if not type_workset_param.IsReadOnly:
                                type_workset_param.Set(workset.Id.IntegerValue)
                                success = True
                            else:
                                logger.error("Type Workset Parameter is read-only")
                        if not success and not existing_ws:
                            workset_table = doc.GetWorksetTable()
                            workset_table.DeleteWorkset(
                                doc, workset.Id, DB.DeleteWorksetSettings()
                            )
                    except Exception as e:
                        logger.error(
                            "Error setting Workset for: {}\nError: {}".format(
                                linked_model_name, e
                            )
                        )
    else:
        if set_all:
            alert(translations_dict["Alert.NoLinksFound.Message"])
        else:
            alert(translations_dict["Alert.SelectOne.Message"])


if __name__ == "__main__":
    main()
