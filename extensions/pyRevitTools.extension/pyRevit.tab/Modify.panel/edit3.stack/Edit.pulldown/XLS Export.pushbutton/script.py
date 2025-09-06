import xlsxwriter
import os
from collections import namedtuple

from pyrevit import script, forms, coreutils, revit, traceback
from pyrevit import DB

itemplate = forms.utils.load_ctrl_template(
    os.path.join(forms.XAML_FILES_DIR, "ParameterItemStyle.xaml")
)
logger = script.get_logger()
doc = revit.doc

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
                    # param_defs_dict[def_name] = forms.ParamDef(
                    #     name=def_name,
                    #     istype=False,
                    #     definition=p.Definition,
                    #     isreadonly=p.IsReadOnly,
                    # )
                    param_def = ParamDef(
                        name=def_name,
                        istype=False,
                        definition=p.Definition,
                        isreadonly=p.IsReadOnly,
                        storagetype=p.StorageType,
                        usermodifiable=p.UserModifiable,
                    )
                    param_defs_dict[def_name] = param_def

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
    file_path = forms.save_file(file_ext=".xlsx", default_name=default_name)
    if not file_path:
        raise ValueError("No file path set")
    workbook = xlsxwriter.Workbook(file_path)
    worksheet = workbook.add_worksheet("Export")

    # Styles
    bold = workbook.add_format({"bold": True})

    # Header row
    worksheet.freeze_panes(1, 0)
    worksheet.write(0, 0, "ElementId", bold)
    for col_idx, param in enumerate(selected_params):
        header_format = bold
        if param.usermodifiable:
            header_format = workbook.add_format({"bold": True, "bg_color": "#B7FD5C"})
        if param.storagetype == DB.StorageType.ElementId:
            header_format = workbook.add_format({"bold": True, "bg_color": "#FFBD80"})
        if param.isreadonly:
            header_format = workbook.add_format({"bold": True, "bg_color": "#FF3131"})
        worksheet.write(0, col_idx + 1, param.name, header_format)

    # Content rows
    max_widths = [len("ElementId")] + [len(p.name) for p in selected_params]

    for row_idx, el in enumerate(src_elements, start=1):
        worksheet.write(row_idx, 0, str(el.Id.IntegerValue))
        for col_idx, param in enumerate(selected_params):
            param_name = param.name
            param_val = el.LookupParameter(param_name)
            val = "<does not exist>"
            if param_val:
                val = ""
                if param_val.HasValue:
                    try:
                        if param_val.StorageType == DB.StorageType.Double:
                            val = param_val.AsValueString()
                        elif param_val.StorageType == DB.StorageType.String:
                            val = param_val.AsString()
                        elif param_val.StorageType == DB.StorageType.Integer:
                            val = str(param_val.AsInteger())
                        elif param_val.StorageType == DB.StorageType.ElementId:
                            val = param_val.AsValueString()
                        else:
                            val = "<unsupported>"
                    except Exception:
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
        instances = (
            DB.FilteredElementCollector(doc)
            .OfClass(DB.FamilyInstance)
            .WhereElementIsNotElementType()
            .ToElements()
        )
        instances = [i for i in instances if not i.SuperComponent]
        src_elements = select_types(instances)
        selected_params = select_parameters(src_elements)
        export_xls(src_elements, selected_params)
    except Exception as e:
        logger.error("Error: {}".format(e))
        logger.error("Traceback: {}".format(traceback.print_exc()))


if __name__ == "__main__":
    main()
