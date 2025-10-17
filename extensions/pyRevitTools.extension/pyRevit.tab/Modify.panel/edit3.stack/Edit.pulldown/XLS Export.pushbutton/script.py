import xlsxwriter
import os
import re
from collections import namedtuple

from pyrevit import script, forms, coreutils, revit, traceback, DB
from pyrevit.compat import get_elementid_value_func

get_elementid_value = get_elementid_value_func()

itemplate = forms.utils.load_ctrl_template(
    os.path.join(forms.XAML_FILES_DIR, "ParameterItemStyle.xaml")
)
script.get_output().close_others()
logger = script.get_logger()
doc = revit.doc
active_view = revit.active_view
project_units = doc.GetUnits()

my_config = script.get_config("xlseximport")
SCOPE = my_config.get_option("scope", "document")
EXPORTUNIT = my_config.get_option("exportunit", "ValueString")

unit_postfix_pattern = re.compile(r"\[.*\]")

ParamDef = namedtuple(
    "ParamDef",
    ["name", "istype", "definition", "isreadonly", "storagetype"],
)


def select_types(instances):
    type_instance_map = {}
    label_map = {}

    for el in instances:
        if not el.Category or el.Category.IsTagCategory:
            continue

        try:
            category = el.Category.Name
            family = (
                el.Symbol.Family.Name
                if hasattr(el, "Symbol") and el.Symbol
                else "NoFamily"
            )
            type_name = el.Name if hasattr(el, "Name") else "NoType"

            key = (category, family, type_name)
            if key not in type_instance_map:
                type_instance_map[key] = []
            type_instance_map[key].append(el)
        except Exception as e:
            logger.warning("Skipping element {}: {}".format(el.Id, e))
            continue

    all_labels = []
    category_groups = {}

    for key, instances in type_instance_map.items():
        category, family, type_name = key
        count = len(instances)
        label = "[{} : {}] {} ({} instances)".format(category, family, type_name, count)

        label_map[label] = key
        all_labels.append(label)

        if category not in category_groups:
            category_groups[category] = []
        category_groups[category].append(label)

    grouped_selection = {"<<All>>": sorted(all_labels)}
    for cat, labels in category_groups.items():
        grouped_selection[cat] = sorted(labels)

    selected_labels = forms.SelectFromList.show(
        grouped_selection,
        title="Select Types to Export Instances Of",
        group_selector_title="Filter by Category:",
        multiselect=True,
    )

    if not selected_labels:
        raise ValueError("No Instances selected")

    selected_keys = [label_map[label] for label in selected_labels]

    src_elements = []
    for key in selected_keys:
        src_elements.extend(type_instance_map[key])

    return src_elements


def select_schedule():
    """Select a schedule from the project."""
    all_schedules = (
        DB.FilteredElementCollector(doc).OfClass(DB.ViewSchedule).ToElements()
    )

    valid_schedules = []
    for schedule in all_schedules:
        try:
            if (
                hasattr(schedule.Definition, "IsInternalKeynoteSchedule")
                and schedule.Definition.IsInternalKeynoteSchedule
            ):
                continue
            if (
                hasattr(schedule.Definition, "IsRevisionSchedule")
                and schedule.Definition.IsRevisionSchedule
            ):
                continue
            if schedule.ViewType == DB.ViewType.Schedule:
                valid_schedules.append(schedule)
        except Exception as e:
            logger.debug("Skipping schedule {}: {}".format(schedule.Name, e))
            continue

    if not valid_schedules:
        raise ValueError("No valid schedules found in project")

    schedule_dict = {}
    for schedule in valid_schedules:
        try:
            category_name = schedule.Definition.CategoryId
            if category_name and category_name != DB.ElementId.InvalidElementId:
                cat = DB.Category.GetCategory(doc, schedule.Definition.CategoryId)
                if cat:
                    category_name = cat.Name
                else:
                    category_name = "Unknown"
            else:
                category_name = "Multi-Category"

            label = "{} ({})".format(schedule.Name, category_name)
            schedule_dict[label] = schedule
        except Exception as e:
            logger.warning("Error processing schedule {}: {}".format(schedule.Name, e))
            continue

    if not schedule_dict:
        raise ValueError("No valid schedules could be processed")

    selected_label = forms.SelectFromList.show(
        sorted(schedule_dict.keys()),
        title="Select Schedule to Export",
        multiselect=False,
    )

    if not selected_label:
        raise ValueError("No schedule selected")

    return schedule_dict[selected_label]


def get_schedule_elements_and_params(schedule):
    """Get elements and parameters from a schedule."""
    schedule_def = schedule.Definition

    visible_fields = []
    param_defs_dict = {}
    non_storage_type = coreutils.get_enum_none(DB.StorageType)

    for field_id in schedule_def.GetFieldOrder():
        field = schedule_def.GetField(field_id)
        if field.IsHidden:
            continue

        if field.IsCalculatedField:
            logger.warning("Skipping calculated field: {}".format(field.GetName()))
            continue

        param_id = field.ParameterId
        if param_id and param_id != DB.ElementId.InvalidElementId:
            visible_fields.append(field)

    collector = DB.FilteredElementCollector(doc, schedule.Id)

    elements = []
    for el in collector:
        if not el.Category or el.Category.IsTagCategory:
            continue
        elements.append(el)

    if not elements:
        raise ValueError("No elements found in schedule")

    for field in visible_fields:
        param_id = field.ParameterId
        for el in elements:
            param = None
            try:
                param = el.get_Parameter(param_id)
            except Exception:
                field_name = field.GetName()
                if field_name:
                    param = el.LookupParameter(field_name)

            if param and param.StorageType != non_storage_type:
                def_name = param.Definition.Name
                if def_name not in param_defs_dict:
                    param_defs_dict[def_name] = ParamDef(
                        name=def_name,
                        istype=False,
                        definition=param.Definition,
                        isreadonly=param.IsReadOnly,
                        storagetype=param.StorageType,
                    )
                break

    param_defs = sorted(param_defs_dict.values(), key=lambda pd: pd.name)

    if not param_defs:
        raise ValueError("No valid parameters found in schedule")

    return elements, param_defs


def select_parameters(src_elements):
    param_defs_dict = {}
    non_storage_type = coreutils.get_enum_none(DB.StorageType)

    for el in src_elements:
        for p in el.Parameters:
            if p.StorageType != non_storage_type:
                def_name = p.Definition.Name
                if def_name not in param_defs_dict:
                    param_defs_dict[def_name] = ParamDef(
                        name=def_name,
                        istype=False,
                        definition=p.Definition,
                        isreadonly=p.IsReadOnly,
                        storagetype=p.StorageType,
                    )

    param_defs = sorted(param_defs_dict.values(), key=lambda pd: pd.name)

    selected_params = forms.SelectFromList.show(
        param_defs,
        width=450,
        multiselect=True,
        item_template=itemplate,
        title="Select Parameters to Export",
    )
    if not selected_params:
        raise ValueError("No Parameter selected")

    return selected_params


def export_xls(src_elements, selected_params):
    default_name = "Export_{}.xlsx".format(
        doc.Title.replace(".rvt", "").replace(" ", "_")
    )
    file_path = forms.save_file(file_ext="xlsx", default_name=default_name)
    if not file_path:
        raise ValueError("No file path set")
    workbook = xlsxwriter.Workbook(file_path)
    worksheet = workbook.add_worksheet("Export")

    bold = workbook.add_format({"bold": True})

    worksheet.freeze_panes(1, 0)
    worksheet.write(0, 0, "ElementId", bold)

    valid_params = []
    for param in selected_params:
        if unit_postfix_pattern.search(param.name):
            logger.warning(
                "Dropping {} from export. [] is not supported.".format(param.name)
            )
            continue
        valid_params.append(param)

    for col_idx, param in enumerate(valid_params):
        postfix = ""  # Reset postfix for each column
        header_format = bold

        if param.storagetype == DB.StorageType.ElementId:
            header_format = workbook.add_format({"bold": True, "bg_color": "#FFBD80"})
        if param.isreadonly:
            header_format = workbook.add_format({"bold": True, "bg_color": "#FF3131"})

        if EXPORTUNIT == "Project Unit":
            forge_type_id = param.definition.GetDataType()
            if DB.UnitUtils.IsMeasurableSpec(forge_type_id):
                symbol_type_id = project_units.GetFormatOptions(
                    forge_type_id
                ).GetSymbolTypeId()
                if not symbol_type_id.Empty():
                    symbol = DB.LabelUtils.GetLabelForSymbol(symbol_type_id)
                    postfix = " [" + symbol + "]"

        worksheet.write(0, col_idx + 1, param.name + postfix, header_format)

    max_widths = [len("ElementId")] + [len(p.name) for p in valid_params]

    for row_idx, el in enumerate(src_elements, start=1):
        worksheet.write(row_idx, 0, str(get_elementid_value(el.Id)))

        for col_idx, param in enumerate(valid_params):
            param_name = param.name
            param_val = el.LookupParameter(param_name)
            val = "<does not exist>"

            if param_val:
                val = ""
                if param_val.HasValue:
                    try:
                        if param_val.StorageType == DB.StorageType.Double:
                            forge_type_id = param.definition.GetDataType()
                            if (
                                DB.UnitUtils.IsMeasurableSpec(forge_type_id)
                                and EXPORTUNIT == "ValueString"
                            ):
                                val = param_val.AsValueString()
                            elif (
                                DB.UnitUtils.IsMeasurableSpec(forge_type_id)
                                and EXPORTUNIT == "Project Unit"
                            ):
                                unit_type_id = param_val.GetUnitTypeId()
                                val = param_val.AsDouble()
                                val = DB.UnitUtils.ConvertFromInternalUnits(
                                    val, unit_type_id
                                )
                            else:
                                val = param_val.AsDouble()
                        elif param_val.StorageType == DB.StorageType.String:
                            val = param_val.AsString()
                        elif param_val.StorageType == DB.StorageType.Integer:
                            val = str(param_val.AsInteger())
                        elif param_val.StorageType == DB.StorageType.ElementId:
                            val = param_val.AsValueString()
                        else:
                            val = "<unsupported>"
                    except Exception as e:
                        logger.warning(
                            "Error reading param '{}' from element {}: {}".format(
                                param_name, el.Id, e
                            )
                        )
                        val = "<Error>"

            worksheet.write(row_idx, col_idx + 1, val)
            if len(str(val)) > max_widths[col_idx + 1]:
                max_widths[col_idx + 1] = min(len(str(val)), 50)

    for col_idx, width in enumerate(max_widths):
        worksheet.set_column(col_idx, col_idx, width + 2)

    worksheet.autofilter(0, 0, len(src_elements), len(valid_params))

    workbook.close()
    logger.info("Exported {} elements to {}".format(len(src_elements), file_path))


def main():
    try:
        if SCOPE == "schedule":
            schedule = select_schedule()
            src_elements, selected_params = get_schedule_elements_and_params(schedule)

        elif SCOPE == "document":
            elements = revit.query.get_all_elements(doc)
            src_elements = select_types(elements)
            selected_params = select_parameters(src_elements)

        elif SCOPE == "current view":
            elements = revit.query.get_all_elements_in_view(active_view)
            src_elements = select_types(elements)
            selected_params = select_parameters(src_elements)

        elif SCOPE == "selection":
            elements = revit.get_selection()
            if not elements:
                elements = revit.pick_elements(message="Pick Elements to Export")

            src_elements = select_types(elements)
            selected_params = select_parameters(src_elements)

        export_xls(src_elements, selected_params)

    except Exception as e:
        logger.error("Error: {}".format(e))
        logger.error(traceback.format_exc())


if __name__ == "__main__":
    main()
