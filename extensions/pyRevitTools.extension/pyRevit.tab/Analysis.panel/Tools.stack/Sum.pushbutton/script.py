# -*- coding: utf-8 -*-
"""Sum a numeric parameter over the selected elements.

Totals are shown in the display units of the project, so metric and imperial
projects both report in the units their users work in.
"""

from collections import OrderedDict, namedtuple

from pyrevit import forms, script
from pyrevit import HOST_APP
from pyrevit import revit, DB
from pyrevit.compat import safe_strtype
from pyrevit.coreutils import applocales, pyutils
from pyrevit.revit import query

from outputtext import escape_for_output

logger = script.get_logger()
output = script.get_output()

RESOURCES = script.get_bundle_file("resources.xaml")

ParamDef = namedtuple("ParamDef", ["name", "type", "spec"])


def _t(key):
    return applocales.get_locale_string_from_xaml(RESOURCES, key)


def is_calculable_param(param):
    if HOST_APP.is_newer_than(2021) and not param.Definition.GetDataType().TypeId:
        return False

    if param.StorageType == DB.StorageType.Double:
        return True

    if param.StorageType == DB.StorageType.Integer:
        val_str = param.AsValueString()
        if val_str and safe_strtype(val_str).lower().isdigit():
            return True

    return False


def get_definition_type(definition):
    if HOST_APP.is_newer_than(2021):
        return definition.GetDataType()
    return definition.UnitType


def get_definition_spec(definition):
    if HOST_APP.is_newer_than(2021):
        return DB.LabelUtils.GetLabelForSpec(definition.GetDataType())
    return DB.LabelUtils.GetLabelFor(definition.ParameterType)


def read_numeric_value(element, param_name):
    """Return the internal value of a numeric parameter, from the element or else its type.

    Returns:
        float: The value, or 0.0 when the parameter is missing or not numeric.
    """
    param = query.get_param(element, param_name)
    if not param:
        element_type = revit.doc.GetElement(element.GetTypeId())
        param = query.get_param(element_type, param_name) if element_type else None
    if not param:
        logger.error(
            "Element with ID: {} does not have parameter: {}.".format(
                element.Id, param_name
            )
        )
        return 0.0
    value = query.get_param_value(param)
    return float(value) if isinstance(value, (int, float)) else 0.0


def is_measurable(param_def):
    if HOST_APP.is_newer_than(2021):
        return DB.UnitUtils.IsMeasurableSpec(param_def.type)
    return param_def.type != DB.UnitType.UT_Undefined


def display_unit_label(param_def):
    """Return the name of the project's display unit, or "" for unitless parameters."""
    if not is_measurable(param_def):
        return ""
    format_options = revit.doc.GetUnits().GetFormatOptions(param_def.type)
    if HOST_APP.is_newer_than(2021):
        return DB.LabelUtils.GetLabelForUnit(format_options.GetUnitTypeId())
    return DB.LabelUtils.GetLabelFor(format_options.DisplayUnits)


def format_value(value, param_def):
    """Format an internal value in the display units of the project.

    Parameters without a unit, such as integers, are shown as plain numbers.
    """
    if not is_measurable(param_def):
        return str(int(value)) if value == int(value) else "{:.2f}".format(value)
    units = revit.doc.GetUnits()
    if HOST_APP.is_newer_than(2021):
        return DB.UnitFormatUtils.Format(units, param_def.type, value, False)
    return DB.UnitFormatUtils.Format(units, param_def.type, value, False, False)


def find_shared_params(element_list):
    """Return the numeric parameters present on every selected element or its type."""
    param_sets = []
    for element in element_list:
        shared_params = set()
        element_type = revit.doc.GetElement(element.GetTypeId())
        owners = [element]
        if element_type and element_type.Id != DB.ElementId.InvalidElementId:
            owners.append(element_type)
        for owner in owners:
            for param in owner.ParametersMap:
                if is_calculable_param(param):
                    definition = param.Definition
                    shared_params.add(
                        ParamDef(
                            definition.Name,
                            get_definition_type(definition),
                            get_definition_spec(definition),
                        )
                    )
        param_sets.append(shared_params)

    if not param_sets:
        return set()
    return set.intersection(*param_sets)


def group_elements(element_list):
    """Group the elements by type name, with the full selection as the first group."""
    groups = pyutils.DefaultOrderedDict(list)
    groups[_t("all_selected")].extend(element_list)
    for element in element_list:
        if hasattr(element, "LineStyle"):
            groups[element.LineStyle.Name].append(element)
        else:
            element_type = revit.doc.GetElement(element.GetTypeId())
            if element_type:
                groups[query.get_name(element_type)].append(element)
    return groups


def report(groups, param_def):
    values_by_group = OrderedDict(
        (
            group_name,
            [
                (element, read_numeric_value(element, param_def.name))
                for element in element_list
            ],
        )
        for group_name, element_list in groups.items()
    )
    unit_label = display_unit_label(param_def)
    unit_suffix = " [{}]".format(escape_for_output(unit_label)) if unit_label else ""
    output.print_md(
        "### {}".format(
            _t("sum_of_parameter").format(escape_for_output(param_def.name))
        )
    )
    output.print_html_table(
        table_data=[
            [
                escape_for_output(group_name),
                len(values),
                format_value(sum(value for _, value in values), param_def),
            ]
            for group_name, values in values_by_group.items()
        ],
        title=_t("summary_title"),
        columns=[
            _t("column_group"),
            _t("column_elements"),
            _t("column_total") + unit_suffix,
        ],
        column_head_align_styles=["left", "right", "right"],
        column_data_align_styles=["left", "right", "right"],
    )
    for group_name, values in values_by_group.items():
        rows = [
            [output.linkify(element.Id), format_value(value, param_def)]
            for element, value in values
        ]
        rows.append(
            [_t("total"), format_value(sum(value for _, value in values), param_def)]
        )
        output.print_html_table(
            table_data=rows,
            title=_t("breakdown_title").format(escape_for_output(group_name)),
            columns=[_t("column_element"), _t("column_value") + unit_suffix],
            last_line_style="font-weight:bold;",
            column_head_align_styles=["left", "right"],
            column_data_align_styles=["left", "right"],
        )


def main():
    selected_elements = revit.get_selection().elements
    options = {
        "{} <{}>".format(param_def.name, param_def.spec): param_def
        for param_def in find_shared_params(selected_elements)
    }
    if not options:
        forms.alert(_t("no_shared_params"), exitscript=True)

    selected_option = forms.CommandSwitchWindow.show(
        sorted(options), message=_t("sum_prompt")
    )
    if not selected_option:
        script.exit()

    report(group_elements(selected_elements), options[selected_option])


if __name__ == "__main__":
    main()
