from collections import namedtuple

from pyrevit import revit, DB, HOST_APP
from pyrevit.compat import safe_strtype
from pyrevit import forms
from pyrevit import script
from pyrevit import coreutils
from pyrevit.coreutils import pyutils


selection = revit.get_selection()

logger = script.get_logger()
output = script.get_output()

ParamDef = namedtuple("ParamDef", ["name", "type", "spec"])


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
    else:
        return definition.ParameterType


def get_definition_spec(definition):
    if HOST_APP.is_newer_than(2021):
        return DB.LabelUtils.GetLabelForSpec(definition.GetDataType())
    else:
        return definition.ParameterType


def calc_param_total(element_list, param_name):
    sum_total = 0.0

    def _add_total(total, param):
        if param.StorageType == DB.StorageType.Double:
            total += param.AsDouble()
        elif param.StorageType == DB.StorageType.Integer:
            total += param.AsInteger()

        return total

    for el in element_list:
        param = el.LookupParameter(param_name)
        if not param:
            el_type = revit.doc.GetElement(el.GetTypeId())
            type_param = el_type.LookupParameter(param_name)
            if not type_param:
                logger.error(
                    "Elemend with ID: {} "
                    "does not have parameter: {}.".format(el.Id, param_name)
                )
            else:
                sum_total = _add_total(sum_total, type_param)
        else:
            sum_total = _add_total(sum_total, param)

    return sum_total


def format_value(total, unit_type):
    format_options = revit.doc.GetUnits().GetFormatOptions(unit_type)
    if HOST_APP.is_newer_than(2021):
        units = format_options.GetUnitTypeId()
        label = DB.LabelUtils.GetLabelForUnit(units)
    else:
        units = format_options.DisplayUnits
        label = DB.LabelUtils.GetLabelFor(units)
    return "{} {}".format(DB.UnitUtils.ConvertFromInternalUnits(total, units), label)


def output_param_total(element_list, param_def):
    total_value = calc_param_total(element_list, param_def.name)

    print("Total value for parameter {} is:\n\n".format(param_def.name))
    try:
        outputstr = format_value(total_value, param_def.type)
    except:
        outputstr = "{}\n".format(total_value)
    print(outputstr)


def output_breakdown(element_list, param_def):
    for element in element_list:
        total_value = calc_param_total([element], param_def.name)
        try:
            outputstr = format_value(total_value, param_def.type)
        except:
            outputstr = "{}\n".format(total_value)
        print("{}\n{}".format(output.linkify(element.Id), outputstr))


def process_options(element_list):
    # find all relevant parameters
    param_sets = []

    for el in element_list:
        shared_params = set()
        # find element parameters
        for param in el.ParametersMap:
            if is_calculable_param(param):
                pdef = param.Definition
                shared_params.add(
                    ParamDef(
                        pdef.Name, get_definition_type(pdef), get_definition_spec(pdef)
                    )
                )

        # find element type parameters
        el_type = revit.doc.GetElement(el.GetTypeId())
        if el_type and el_type.Id != DB.ElementId.InvalidElementId:
            for type_param in el_type.ParametersMap:
                if is_calculable_param(type_param):
                    pdef = type_param.Definition
                    shared_params.add(
                        ParamDef(
                            pdef.Name,
                            get_definition_type(pdef),
                            get_definition_spec(pdef),
                        )
                    )

        param_sets.append(shared_params)

    # make a list of options from discovered parameters
    if param_sets:
        all_shared_params = param_sets[0]
        for param_set in param_sets[1:]:
            all_shared_params = all_shared_params.intersection(param_set)

        return {"{} <{}>".format(x.name, x.spec): x for x in all_shared_params}


def process_sets(element_list):
    el_sets = pyutils.DefaultOrderedDict(list)

    # add all elements as first set, for totals of all elements
    el_sets["All Selected Elements"].extend(element_list)

    # separate elements into sets based on their type
    for el in element_list:
        if hasattr(el, "LineStyle"):
            el_sets[el.LineStyle.Name].append(el)
        else:
            eltype = revit.doc.GetElement(el.GetTypeId())
            if eltype:
                el_sets[revit.query.get_name(eltype)].append(el)

    return el_sets


# main -----------------------------------------------------------------------
# ask user to select an option
options = process_options(selection.elements)

if options:
    selected_switch = forms.CommandSwitchWindow.show(
        sorted(options), message="Sum values of parameter:"
    )

    # Calculating totals for each set and printing results
    if selected_switch:
        selected_option = options[selected_switch]
        if selected_option:
            for type_name, element_set in process_sets(selection.elements).items():
                type_name = coreutils.escape_for_html(type_name)
                output.print_md("### Totals for: {}".format(type_name))
                output_param_total(element_set, selected_option)
                output.print_md("#### Breakdown:")
                output_breakdown(element_set, selected_option)
                output.insert_divider(level="##")
