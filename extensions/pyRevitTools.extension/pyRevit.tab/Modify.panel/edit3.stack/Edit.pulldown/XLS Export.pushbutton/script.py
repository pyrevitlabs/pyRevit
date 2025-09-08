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
exclude_nested = my_config.get_option("exclude_nested", True)
scope = my_config.get_option("scope", "document")
exportunit = my_config.get_option("exportunit", "ValueString")

unit_postfix_pattern = re.compile(r"\[.*\]")

ParamDef = namedtuple(
    "ParamDef",
    ["name", "istype", "definition", "isreadonly", "storagetype", "usermodifiable"],
)


def select_types(instances):
    # Group by (category, family, type)
    type_instance_map = {}
    label_map = {}  # maps key to display label
    category_groups = {}  # category -> [labels]

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

    # Build label map and category groupings
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

    # Show UI
    selected_labels = forms.SelectFromList.show(
        grouped_selection,
        title="Select Types to Export Instances Of",
        group_selector_title="Filter by Category:",
        multiselect=True,
    )

    if not selected_labels:
        raise ValueError("No Instances selected")

    # Map back selected keys
    selected_keys = [label_map[label] for label in selected_labels]

    # Collect instances for export
    src_elements = []
    for key in selected_keys:
        src_elements.extend(type_instance_map[key])

    return src_elements


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
                        usermodifiable=p.UserModifiable,
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

    # Styles
    bold = workbook.add_format({"bold": True})

    # Header row
    worksheet.freeze_panes(1, 0)
    worksheet.write(0, 0, "ElementId", bold)
    postfix = ""
    for col_idx, param in enumerate(selected_params):
        header_format = bold
        if unit_postfix_pattern.search(param.name):
            logger.warning(
                "Dropping {} from export. [] is not supported.".format(param.name)
            )
            continue
        if param.usermodifiable:
            header_format = workbook.add_format({"bold": True, "bg_color": "#B7FD5C"})
        if param.storagetype == DB.StorageType.ElementId:
            header_format = workbook.add_format({"bold": True, "bg_color": "#FFBD80"})
        if param.isreadonly:
            header_format = workbook.add_format({"bold": True, "bg_color": "#FF3131"})
        if exportunit == "Project Unit":
            forge_type_id = param.definition.GetDataType()
            if DB.UnitUtils.IsMeasurableSpec(forge_type_id):
                symbol_type_id = project_units.GetFormatOptions(
                    forge_type_id
                ).GetSymbolTypeId()
                symbol = DB.LabelUtils.GetLabelForSymbol(symbol_type_id)
                postfix = " [" + symbol + "]"
        worksheet.write(0, col_idx + 1, param.name + postfix, header_format)

    # Content rows
    max_widths = [len("ElementId")] + [len(p.name) for p in selected_params]

    for row_idx, el in enumerate(src_elements, start=1):
        worksheet.write(row_idx, 0, str(get_elementid_value(el.Id)))
        for col_idx, param in enumerate(selected_params):
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
                                and exportunit == "ValueString"
                            ):
                                val = param_val.AsValueString()
                            elif (
                                DB.UnitUtils.IsMeasurableSpec(forge_type_id)
                                and exportunit == "Project Unit"
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
                        print(e)
                        val = "<Error>"

            worksheet.write(row_idx, col_idx + 1, val)
            if len(str(val)) > max_widths[col_idx + 1]:
                max_widths[col_idx + 1] = min(len(str(val)), 50)

    # Set column widths
    for col_idx, width in enumerate(max_widths):
        worksheet.set_column(col_idx, col_idx, width + 2)

    # Enable autofilter
    worksheet.autofilter(0, 0, len(src_elements), len(selected_params))

    workbook.close()
    logger.info("Exported {} elements to {}".format(len(src_elements), file_path))


def main():
    try:
        if scope == "document":
            instances = (
                DB.FilteredElementCollector(doc)
                .OfClass(DB.FamilyInstance)
                .WhereElementIsNotElementType()
                .ToElements()
            )
        elif scope == "current view":
            instances = (
                DB.FilteredElementCollector(doc, active_view.Id)
                .OfClass(DB.FamilyInstance)
                .WhereElementIsNotElementType()
                .ToElements()
            )
        else:
            instances = revit.get_selection()
            if not instances:
                instances = revit.pick_elements(message="Pick Elements to Export")
        if exclude_nested:
            instances = [i for i in instances if not i.SuperComponent]
        src_elements = select_types(instances)
        selected_params = select_parameters(src_elements)
        export_xls(src_elements, selected_params)
    except Exception as e:
        logger.error("Error: {}".format(e))
        logger.error("Traceback: {}".format(traceback.print_exc()))


if __name__ == "__main__":
    main()
