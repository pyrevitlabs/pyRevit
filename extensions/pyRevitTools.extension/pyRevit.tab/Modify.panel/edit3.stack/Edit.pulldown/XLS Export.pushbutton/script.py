import xlsxwriter
import os
import re
from collections import namedtuple

from pyrevit import script, forms, coreutils, revit, traceback, DB, HOST_APP
from pyrevit.revit import get_parameter_data_type, is_yesno_parameter
from pyrevit.compat import get_elementid_value_func

get_elementid_value = get_elementid_value_func()

para_item_xml = os.path.join(forms.XAML_FILES_DIR, "ParameterItemStyle.xaml")
para_itemplate = forms.utils.load_ctrl_template(para_item_xml)
ele_item_xml = script.get_bundle_file("ElementItemStyle.xaml")
ele_itemplate = forms.utils.load_ctrl_template(ele_item_xml)

script.get_output().close_others()
logger = script.get_logger()
doc = revit.doc
active_view = revit.active_view
project_units = doc.GetUnits()

unit_postfix_pattern = re.compile(r"\s*\[.*\]$")

ParamDef = namedtuple(
    "ParamDef", ["name", "istype", "definition", "isreadonly", "isunit", "storagetype"]
)
ElementDef = namedtuple(
    "ElementDef",
    [
        "label",  # Display label for UI
        "category",  # Category name
        "family",  # Family name (or "NoFamily")
        "type_name",  # Type name
        "is_type",  # True if element type, False if instance
        "element_label",  # Description like "type(s)" or "instance(s)"
        "elements",  # List of actual Revit elements
        "count",  # Number of elements in this group
    ],
)


def create_element_definitions(elements):
    """Create element definitions for the given elements."""
    type_element_map = {}

    for el in elements:
        if not el.Category or el.Category.IsTagCategory:
            continue
        try:
            category = el.Category.Name
            is_type = DB.ElementIsElementTypeFilter().PassesFilter(el)
            family = "NoFamily"
            type_name = "NoType"
            element_label = "unknown"

            if is_type:
                type_name = getattr(el, "Name", "Unnamed Type")
                element_label = "type(s)"
            else:
                if isinstance(el, DB.FamilyInstance):
                    family = el.Symbol.Family.Name
                    type_name = el.Symbol.get_Parameter(
                        DB.BuiltInParameter.SYMBOL_NAME_PARAM
                    ).AsString()
                    element_label = "family instance(s)"
                else:
                    type_name = getattr(el, "Name", "Unnamed Instance")
                    element_label = "instance(s)"

            key = (category, family, type_name, is_type, element_label)
            if key not in type_element_map:
                type_element_map[key] = []
            type_element_map[key].append(el)

        except Exception as ex:
            logger.debug(
                "Skipped element ID {}: {}".format(get_elementid_value(el.Id), str(ex))
            )
            continue

    element_defs = []
    for key, element_list in type_element_map.items():
        category, family, type_name, is_type, element_label = key
        count = len(element_list)
        label = "[{} : {}] {}".format(category, family, type_name)

        element_def = ElementDef(
            label=label,
            category=category,
            family=family,
            type_name=type_name,
            is_type=is_type,
            element_label=element_label,
            elements=element_list,
            count=count,
        )
        element_defs.append(element_def)

    return element_defs


def select_elements(elements):
    """Select elements from the given elements."""
    element_defs = create_element_definitions(elements)

    if not element_defs:
        logger.warning("No valid elements found to select from")

    element_defs = sorted(element_defs, key=lambda x: x.label)

    category_groups = {}
    for elem_def in element_defs:
        cat = elem_def.category
        if cat not in category_groups:
            category_groups[cat] = []
        category_groups[cat].append(elem_def)

    grouped_selection = {"<<All>>": element_defs}
    for cat in sorted(category_groups.keys()):
        grouped_selection[cat] = category_groups[cat]

    context = grouped_selection

    selected_defs = forms.SelectFromList.show(
        context,
        title="Select Elements to Export",
        width=500,
        multiselect=True,
        item_template=ele_itemplate,
    )

    if not selected_defs:
        script.exit()

    src_elements = []
    for elem_def in selected_defs:
        src_elements.extend(elem_def.elements)
    return src_elements


def schedule_filter(schedule):
    """Filter out internal and revision schedules. Returns True if the schedule is valid, False otherwise."""
    try:
        if (
            hasattr(schedule.Definition, "IsInternalKeynoteSchedule")
            and schedule.Definition.IsInternalKeynoteSchedule
        ):
            return False
        if (
            hasattr(schedule.Definition, "IsRevisionSchedule")
            and schedule.Definition.IsRevisionSchedule
        ):
            return False
        return True
    except Exception:
        return False


def get_schedule_elements_and_params(schedule):
    """Get elements and parameters from a schedule. Returns a tuple of elements and parameters."""
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
                    param_data_type = get_parameter_data_type(param.Definition)
                    param_defs_dict[def_name] = ParamDef(
                        name=def_name,
                        istype=False,
                        definition=param.Definition,
                        isreadonly=param.IsReadOnly,
                        isunit=DB.UnitUtils.IsMeasurableSpec(param_data_type) if param_data_type else False,
                        storagetype=param.StorageType,
                    )
                break

    param_defs = sorted(param_defs_dict.values(), key=lambda pd: pd.name)

    if not param_defs:
        raise ValueError("No valid parameters found in schedule")

    return elements, param_defs


def select_parameters(src_elements):
    """Select parameters from the given elements. Returns a list of parameters."""
    param_defs_dict = {}
    non_storage_type = coreutils.get_enum_none(DB.StorageType)

    for el in src_elements:
        for p in el.Parameters:
            if p.StorageType != non_storage_type:
                def_name = p.Definition.Name
                if def_name not in param_defs_dict:
                    param_data_type = get_parameter_data_type(p.Definition)
                    param_defs_dict[def_name] = ParamDef(
                        name=def_name,
                        istype=False,
                        definition=p.Definition,
                        isreadonly=p.IsReadOnly,
                        isunit=DB.UnitUtils.IsMeasurableSpec(param_data_type) if param_data_type else False,
                        storagetype=p.StorageType,
                    )

    param_defs = sorted(param_defs_dict.values(), key=lambda pd: pd.name)

    selected_params = forms.SelectFromList.show(
        param_defs,
        width=450,
        multiselect=True,
        item_template=para_itemplate,
        title="Select Parameters to Export",
    )
    if not selected_params:
        script.exit()

    return selected_params


def export_xls(src_elements, selected_params):
    """Export the given elements and parameters to an Excel file."""
    default_name = "Export_{}.xlsx".format(
        doc.Title.replace(".rvt", "").replace(" ", "_")
    )
    file_path = forms.save_file(file_ext="xlsx", default_name=default_name)
    if not file_path:
        raise ValueError("No file path set")
    workbook = xlsxwriter.Workbook(file_path)
    worksheet = workbook.add_worksheet("Export")

    bold = workbook.add_format({"bold": True})
    unlocked = workbook.add_format({"locked": False})
    locked = workbook.add_format({"locked": True})

    worksheet.freeze_panes(1, 0)
    worksheet.write(0, 0, "ElementId", bold)

    valid_params = []
    for param in selected_params:
        if unit_postfix_pattern.search(param.name):
            logger.warning(
                "Dropping {} from export. Parameter name already contains brackets.".format(param.name)
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

        forge_type_id = get_parameter_data_type(param.definition)
        if forge_type_id and DB.UnitUtils.IsMeasurableSpec(forge_type_id):
            symbol_type_id = project_units.GetFormatOptions(
                forge_type_id
            ).GetSymbolTypeId()
            if not symbol_type_id.Empty():
                symbol = DB.LabelUtils.GetLabelForSymbol(symbol_type_id)
                postfix = " [" + symbol + "]"

        worksheet.write(0, col_idx + 1, param.name + postfix, header_format)

    max_widths = [len("ElementId")] + [len(p.name) for p in valid_params]

    for row_idx, el in enumerate(src_elements, start=1):
        worksheet.write(row_idx, 0, str(get_elementid_value(el.Id)), locked)

        for col_idx, param in enumerate(valid_params):
            param_name = param.name
            param_val = el.LookupParameter(param_name)
            val = "<does not exist>"
            cell_format = locked
            if param_val:
                val = ""
                if param_val.HasValue:
                    try:
                        if param_val.StorageType == DB.StorageType.Double:
                            forge_type_id = get_parameter_data_type(param.definition)
                            val = param_val.AsDouble()
                            if forge_type_id and DB.UnitUtils.IsMeasurableSpec(forge_type_id):
                                unit_type_id = param_val.GetUnitTypeId()
                                val = DB.UnitUtils.ConvertFromInternalUnits(
                                    param_val.AsDouble(), unit_type_id
                                )
                        elif param_val.StorageType == DB.StorageType.String:
                            val = param_val.AsString()
                        elif param_val.StorageType == DB.StorageType.Integer:
                            # Check if this is a Yes/No parameter using helper function
                            if is_yesno_parameter(param.definition):
                                val = "Yes" if param_val.AsInteger() else "No"
                            else:
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

                # Cell is unlocked only if parameter exists, has value, and is not read-only
                if not param.isreadonly:
                    cell_format = unlocked
            # If param doesn't exist or has no value, cell remains locked

            worksheet.write(row_idx, col_idx + 1, val, cell_format)
            if len(str(val)) > max_widths[col_idx + 1]:
                max_widths[col_idx + 1] = min(len(str(val)), 50)

    for col_idx, width in enumerate(max_widths):
        worksheet.set_column(col_idx, col_idx, width + 3)

    worksheet.autofilter(0, 0, len(src_elements), len(valid_params))
    worksheet.protect(
        "",
        {
            "autofilter": True,
            "sort": True,
            "format_cells": True,
            "format_columns": True,
            "format_rows": True,
            "delete_columns": True,
            "delete_rows": True,
            "select_locked_cells": True,
            "select_unlocked_cells": True,
        },
    )
    workbook.close()
    logger.info("Exported {} elements to {}".format(len(src_elements), file_path))


def main(advanced=False):
    try:
        if not advanced:
            schedule = forms.select_schedules(
                title="Select Schedule to Export",
                multiple=False,
                filterfunc=schedule_filter,
            )
            if not schedule:
                return
            src_elements, selected_params = get_schedule_elements_and_params(schedule)

        else:
            opts = [
                "Schedule",
                "Document - all",
                "Document - types",
                "Document - instances",
                "Current View",
                "Selection",
            ]
            selection = forms.SelectFromList.show(
                opts, title="Select Export Scope"
            )
            if not selection:
                return
            if selection == "Schedule":
                schedule = forms.select_schedules(
                    title="Select Schedule to Export",
                    multiple=False,
                    filterfunc=schedule_filter,
                )
                if not schedule:
                    return
                src_elements, selected_params = get_schedule_elements_and_params(
                    schedule
                )
            else:
                if "Document" in selection:
                    elements = revit.query.get_all_elements(doc)
                    if selection == "Document - types":
                        type_filter = DB.ElementIsElementTypeFilter()
                        elements = [el for el in elements if type_filter.PassesFilter(el)]

                    elif selection == "Document - instances":
                        type_filter = DB.ElementIsElementTypeFilter(True)
                        elements = [el for el in elements if type_filter.PassesFilter(el)]
                elif selection == "Current View":
                    elements = revit.query.get_all_elements_in_view(active_view)
                elif selection == "Selection":
                    elements = revit.get_selection()
                    if not elements:
                        with forms.WarningBar(title="Pick Elements to Export"):
                            elements = revit.pick_elements(message="Pick Elements to Export")

                src_elements = select_elements(elements)
                selected_params = select_parameters(src_elements)

        export_xls(src_elements, selected_params)

    except Exception as e:
        logger.error("Error: {}".format(e))
        logger.error(traceback.format_exc())


if __name__ == "__main__":
    main()
