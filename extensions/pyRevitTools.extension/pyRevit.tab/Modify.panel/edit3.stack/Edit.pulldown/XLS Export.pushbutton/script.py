import xlsxwriter
import os
import re
from collections import namedtuple

from pyrevit import script, forms, coreutils, revit, DB
from pyrevit.revit import get_parameter_data_type, is_yesno_parameter
from pyrevit.compat import get_elementid_value_func
from pyrevit.userconfig import user_config

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
BIP = DB.BuiltInParameter
measurable = DB.UnitUtils.IsMeasurableSpec

unit_postfix_pattern = re.compile(r"\s*\[.*\]$")

ParamDef = namedtuple(
    "ParamDef",
    [
        "name",
        "istype",
        "definition",
        "isreadonly",
        "isunit",
        "storagetype",
        "forge_type_id",
        "unit_type_id",
    ],
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


class ElementSelectFromList(forms.SelectFromList):
    """Custom SelectFromList that merges ElementItemStyle resource dictionaries."""

    def _setup(self, **kwargs):
        # Merge ElementItemStyle resource dictionaries
        ele_item_resfile = ele_item_xml.replace(
            ".xaml", ".ResourceDictionary.{}.xaml".format(user_config.user_locale)
        )
        ele_item_resfile_en = ele_item_xml.replace(
            ".xaml", ".ResourceDictionary.en_us.xaml"
        )

        if os.path.isfile(ele_item_resfile):
            self.merge_resource_dict(ele_item_resfile)
        elif os.path.isfile(ele_item_resfile_en):
            self.merge_resource_dict(ele_item_resfile_en)

        # Call parent _setup
        super(ElementSelectFromList, self)._setup(**kwargs)


def get_unit_label_and_value(param, forge_type_id, field, project_units):
    """
    Returns (converted_value, label_string, unit_type_id, symbol_type_id) for a parameter.
    Respects schedule field overrides if provided, otherwise uses project units.
    """
    if not forge_type_id or not measurable(forge_type_id):
        return param.AsValueString(), "", None, None

    # Prefer field overrides, otherwise project units
    fmt_opts = None
    if field:
        try:
            field_fmt = field.GetFormatOptions()
            # Only use field format if it's not using defaults
            if field_fmt and not field_fmt.UseDefault:
                fmt_opts = field_fmt
        except Exception:
            pass

    # Fall back to project units if no valid field override
    if not fmt_opts:
        fmt_opts = project_units.GetFormatOptions(forge_type_id)

    # Check UseDefault before accessing unit type
    if fmt_opts.UseDefault:
        # Should not happen with project units, but handle it safely
        fmt_opts = project_units.GetFormatOptions(forge_type_id)

    unit_id = fmt_opts.GetUnitTypeId()
    symbol_id = fmt_opts.GetSymbolTypeId()

    # Convert
    val = DB.UnitUtils.ConvertFromInternalUnits(param.AsDouble(), unit_id)

    # Label
    label = ""
    try:
        label = DB.LabelUtils.GetLabelForSymbol(symbol_id)
    except Exception:
        try:
            label = DB.LabelUtils.GetLabelForUnit(unit_id)
        except Exception:
            label = ""

    return val, "[{}]".format(label) if label else "", unit_id, symbol_id


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
                        BIP.SYMBOL_NAME_PARAM
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

    selected_defs = ElementSelectFromList.show(
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
    schedule_def = schedule.Definition

    visible_fields = []
    param_defs_list = []
    field_mapping = {}
    non_storage_type = coreutils.get_enum_none(DB.StorageType)
    processed_params = set()

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
                if def_name not in processed_params:
                    param_data_type = get_parameter_data_type(param.Definition)

                    unit_type_id = None
                    if param_data_type and measurable(param_data_type):
                        try:
                            fmt_opts = field.GetFormatOptions()
                            if fmt_opts:
                                unit_type_id = fmt_opts.GetUnitTypeId()
                        except Exception:
                            pass

                    param_defs_list.append(ParamDef(
                        name=def_name,
                        istype=False,
                        definition=param.Definition,
                        isreadonly=param.IsReadOnly,
                        isunit=(
                            measurable(param_data_type)
                            if param_data_type
                            else False
                        ),
                        storagetype=param.StorageType,
                        forge_type_id=param_data_type,
                        unit_type_id=unit_type_id,
                    ))
                    field_mapping[def_name] = field
                    processed_params.add(def_name)
                break

    if not param_defs_list:
        raise ValueError("No valid parameters found in schedule")

    return elements, param_defs_list, field_mapping


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

                    # For non-schedule exports, use project units
                    unit_type_id = None
                    if param_data_type and measurable(param_data_type):
                        try:
                            fmt_opts = project_units.GetFormatOptions(param_data_type)
                            unit_type_id = fmt_opts.GetUnitTypeId()
                        except Exception:
                            pass

                    param_defs_dict[def_name] = ParamDef(
                        name=def_name,
                        istype=False,
                        definition=p.Definition,
                        isreadonly=p.IsReadOnly,
                        isunit=(
                            measurable(param_data_type)
                            if param_data_type
                            else False
                        ),
                        storagetype=p.StorageType,
                        forge_type_id=param_data_type,
                        unit_type_id=unit_type_id,
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


def create_dropdown_validation(
    worksheet, workbook, col_idx, param, src_elements, hidden_sheets
):
    """
    Create dropdown validation for ElementId and Workset parameters.

    Args:
        worksheet: The main worksheet
        workbook: The workbook object
        col_idx: Column index (0-based)
        param: ParamDef namedtuple
        src_elements: List of source elements
        hidden_sheets: Dict to track created hidden sheets
    """
    storage_type = param.storagetype

    if storage_type == DB.StorageType.Integer:
        if param.definition.BuiltInParameter == BIP.ELEM_PARTITION_PARAM:
            try:
                # worksets = DB.FilteredWorksetCollector(doc).OfKind(DB.WorksetKind.UserWorkset)
                worksets = DB.FilteredWorksetCollector(doc)
                workset_names = sorted([ws.Name for ws in worksets if ws.Name])

                if workset_names:
                    hidden_sheet_name = "_worksets"

                    if hidden_sheet_name not in hidden_sheets:
                        hidden_sheet = workbook.add_worksheet(hidden_sheet_name)
                        hidden_sheet.hide()
                        hidden_sheets[hidden_sheet_name] = hidden_sheet

                        # Write workset names to hidden sheet
                        for idx, name in enumerate(workset_names):
                            hidden_sheet.write(idx, 0, name)

                    formula = "={}!$A$1:$A${}".format(
                        hidden_sheet_name, len(workset_names)
                    )

                    worksheet.data_validation(
                        1,
                        col_idx,
                        len(src_elements),
                        col_idx,
                        {
                            "validate": "list",
                            "source": formula,
                            "error_message": "Please select a valid workset",
                            "error_type": "stop",
                        },
                    )

            except Exception as e:
                logger.warning(
                    "Could not create workset dropdown for '{}': {}".format(
                        param.name, e
                    )
                )

    elif storage_type == DB.StorageType.ElementId:
        try:
            sample_category = None

            for el in src_elements:
                param_el = el.LookupParameter(param.name)
                if param_el and param_el.HasValue:
                    el_id = param_el.AsElementId()
                    if el_id and el_id != DB.ElementId.InvalidElementId:
                        ref_element = doc.GetElement(el_id)
                        if (
                            ref_element
                            and hasattr(ref_element, "Category")
                            and ref_element.Category
                        ):
                            sample_category = ref_element.Category.BuiltInCategory
                            break

            if sample_category is not None:
                collector = revit.query.get_elements_by_categories([sample_category])
                element_names = sorted(
                    list(
                        set(
                            [
                                el.Name
                                for el in collector
                                if hasattr(el, "Name") and el.Name
                            ]
                        )
                    )
                )

                if element_names:
                    safe_param_name = (
                        re.sub(r"[^\w\s-]", "", param.name).strip().replace(" ", "_")
                    )
                    hidden_sheet_name = "_elem_{}".format(
                        safe_param_name[:25]
                    )  # Limit sheet name length

                    if hidden_sheet_name not in hidden_sheets:
                        hidden_sheet = workbook.add_worksheet(hidden_sheet_name)
                        hidden_sheet.hide()
                        hidden_sheets[hidden_sheet_name] = hidden_sheet

                        for idx, name in enumerate(element_names):
                            hidden_sheet.write(idx, 0, name)

                    formula = "={}!$A$1:$A${}".format(
                        hidden_sheet_name, len(element_names)
                    )

                    worksheet.data_validation(
                        1,
                        col_idx,
                        len(src_elements),
                        col_idx,
                        {
                            "validate": "list",
                            "source": formula,
                            "error_message": "Please select a valid element",
                            "error_type": "stop",
                        },
                    )

        except Exception as e:
            logger.warning(
                "Could not create ElementId dropdown for '{}': {}".format(param.name, e)
            )


def export_xls(src_elements, selected_params, field_mapping=None):
    """
    Export the given elements and parameters to an Excel file.
    field_mapping is an optional dict {param_name: field} for schedule overrides.
    """
    default_name = "Export_{}.xlsx".format(
        doc.Title.replace(".rvt", "").replace(" ", "_")
    )
    file_path = forms.save_file(file_ext="xlsx", default_name=default_name)
    if not file_path:
        raise ValueError("No file path set")
    workbook = xlsxwriter.Workbook(file_path)
    worksheet = workbook.add_worksheet("Export")
    metadata_sheet = workbook.add_worksheet("_metadata")
    metadata_sheet.hide()

    # Track hidden sheets for dropdowns
    hidden_sheets = {}

    bold = workbook.add_format({"bold": True})
    unlocked = workbook.add_format({"locked": False})
    locked = workbook.add_format({"locked": True})

    worksheet.freeze_panes(1, 0)
    worksheet.write(0, 0, "ElementId", bold)

    # Write metadata headers
    metadata_sheet.write(0, 0, "Parameter Name", bold)
    metadata_sheet.write(0, 1, "ForgeTypeId", bold)
    metadata_sheet.write(0, 2, "UnitTypeId", bold)
    metadata_sheet.write(0, 3, "SymbolTypeId", bold)
    metadata_sheet.write(0, 4, "IsScheduleOverride", bold)

    valid_params = []
    for param in selected_params:
        if unit_postfix_pattern.search(param.name):
            logger.warning(
                "Dropping {} from export. Parameter name already contains brackets.".format(
                    param.name
                )
            )
            continue
        valid_params.append(param)

    if field_mapping is None:
        field_mapping = {}

    for col_idx, param in enumerate(valid_params):
        postfix = ""  # Reset postfix for each column
        header_format = bold

        if param.storagetype == DB.StorageType.ElementId:
            header_format = workbook.add_format({"bold": True, "bg_color": "#FFBD80"})
        if param.isreadonly:
            header_format = workbook.add_format({"bold": True, "bg_color": "#FF3131"})

        forge_type_id = param.forge_type_id
        unit_type_id = None
        symbol_type_id = None
        is_schedule_override = param.name in field_mapping

        if forge_type_id and measurable(forge_type_id):
            # Get field for this parameter if available
            field = field_mapping.get(param.name)

            # Get format options (field override or project units)
            fmt_opts = None
            if field:
                try:
                    field_fmt = field.GetFormatOptions()
                    # Only use field format if it's not using defaults
                    if field_fmt and not field_fmt.UseDefault:
                        fmt_opts = field_fmt
                except Exception:
                    pass

            # Fall back to project units if no valid field override
            if not fmt_opts:
                fmt_opts = project_units.GetFormatOptions(forge_type_id)

            # Check UseDefault before accessing unit type
            if not fmt_opts.UseDefault:
                unit_type_id = fmt_opts.GetUnitTypeId()
                symbol_type_id = fmt_opts.GetSymbolTypeId()

                if not symbol_type_id.Empty():
                    try:
                        symbol = DB.LabelUtils.GetLabelForSymbol(symbol_type_id)
                        postfix = " [" + symbol + "]"
                    except Exception:
                        try:
                            symbol = DB.LabelUtils.GetLabelForUnit(unit_type_id)
                            postfix = " [" + symbol + "]"
                        except Exception:
                            pass

        worksheet.write(0, col_idx + 1, param.name + postfix, header_format)

        # Write metadata for this parameter
        metadata_sheet.write(col_idx + 1, 0, param.name)
        metadata_sheet.write(
            col_idx + 1, 1, forge_type_id.TypeId if forge_type_id else ""
        )
        metadata_sheet.write(
            col_idx + 1, 2, unit_type_id.TypeId if unit_type_id else ""
        )
        metadata_sheet.write(
            col_idx + 1, 3, symbol_type_id.TypeId if symbol_type_id else ""
        )
        metadata_sheet.write(col_idx + 1, 4, "Yes" if is_schedule_override else "No")

    max_widths = [len("ElementId")] + [len(p.name) for p in valid_params]

    for row_idx, el in enumerate(src_elements, start=1):
        worksheet.write(row_idx, 0, str(get_elementid_value(el.Id)), locked)

        for col_idx, param in enumerate(valid_params):
            param_name = param.name
            param_el = el.LookupParameter(param_name)
            val = "<does not exist>"
            cell_format = locked
            if param_el:
                val = ""
                if param_el.HasValue:
                    try:
                        if param_el.StorageType == DB.StorageType.Double:
                            forge_type_id = param.forge_type_id
                            field = field_mapping.get(param_name)

                            if forge_type_id and measurable(forge_type_id):
                                val, _, _, _ = get_unit_label_and_value(
                                    param_el, forge_type_id, field, project_units
                                )
                            else:
                                val = param_el.AsDouble()
                        elif param_el.StorageType == DB.StorageType.String:
                            val = param_el.AsString()
                        elif param_el.StorageType == DB.StorageType.Integer:
                            if get_elementid_value(param_el.Id) == int(BIP.ELEM_PARTITION_PARAM):
                                val = str(revit.query.get_element_workset(el).Name)
                            elif is_yesno_parameter(param.definition):
                                val = "Yes" if param_el.AsInteger() else "No"
                            else:
                                val = str(param_el.AsInteger())
                        elif param_el.StorageType == DB.StorageType.ElementId:
                            val = param_el.AsValueString()
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

    for col_idx, param in enumerate(valid_params):
        create_dropdown_validation(
            worksheet,
            workbook,
            col_idx + 1,  # +1 because column 0 is ElementId
            param,
            src_elements,
            hidden_sheets,
        )

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
            src_elements, selected_params, field_mapping = (
                get_schedule_elements_and_params(schedule)
            )
            export_xls(src_elements, selected_params, field_mapping)

        else:
            opts = [
                "Schedule",
                "Document - all",
                "Document - types",
                "Document - instances",
                "Current View",
                "Selection",
            ]
            selection = forms.SelectFromList.show(opts, title="Select Export Scope")
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
                src_elements, selected_params, field_mapping = (
                    get_schedule_elements_and_params(schedule)
                )
                export_xls(src_elements, selected_params, field_mapping)
            else:
                if "Document" in selection:
                    elements = revit.query.get_all_elements(doc)
                    if selection == "Document - types":
                        type_filter = DB.ElementIsElementTypeFilter()
                        elements = [
                            el for el in elements if type_filter.PassesFilter(el)
                        ]

                    elif selection == "Document - instances":
                        type_filter = DB.ElementIsElementTypeFilter(True)
                        elements = [
                            el for el in elements if type_filter.PassesFilter(el)
                        ]
                elif selection == "Current View":
                    elements = revit.query.get_all_elements_in_view(active_view)
                elif selection == "Selection":
                    elements = revit.get_selection()
                    if not elements:
                        with forms.WarningBar(title="Pick Elements to Export"):
                            elements = revit.pick_elements(
                                message="Pick Elements to Export"
                            )

                src_elements = select_elements(elements)
                selected_params = select_parameters(src_elements)
                # No field mapping for non-schedule exports
                export_xls(src_elements, selected_params, field_mapping=None)

    except Exception as e:
        logger.exception("Error: {}".format(e))


if __name__ == "__main__":
    main()
