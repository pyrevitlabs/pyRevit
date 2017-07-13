from scriptutils import logger
from scriptutils.userinput import CommandSwitchWindow
from revitutils import doc, selection

from collections import namedtuple

ParamDef = namedtuple('ParamDef', ['name', 'type'])

# noinspection PyUnresolvedReferences
from Autodesk.Revit.DB import CurveElement, ElementId, \
                              StorageType, ParameterType

__doc__ = 'Sums up the values of selected parameter on selected elements. ' \
          'This tool studies the selected elements and their associated '   \
          'types and presents the user with a list of parameters that are ' \
          'shared between the selected elements. Only parameters with '     \
          'Double or Interger values are included.'

__title__ = 'Sum Total'


def is_calculable_param(param):
    if param.StorageType == StorageType.Double:
        return True

    if param.StorageType == StorageType.Integer:
        val_str = param.AsValueString()
        if val_str and unicode(val_str).lower().isdigit():
            return True

    return False


def calc_param_total(element_list, param_name):
    sum_total = 0.0

    def _add_total(total, param):
        if param.StorageType == StorageType.Double:
            total += param.AsDouble()
        elif param.StorageType == StorageType.Integer:
            total += param.AsInteger()

        return total

    for el in element_list:
        param = el.LookupParameter(param_name)
        if not param:
            el_type = doc.GetElement(el.GetTypeId())
            type_param = el_type.LookupParameter(param_name)
            if not type_param:
                logger.error('Elemend with ID: {} '
                             'does not have parameter: {}.'.format(el.Id,
                                                                   param_name))
            else:
                sum_total = _add_total(sum_total, type_param)
        else:
            sum_total = _add_total(sum_total, param)

    return sum_total


def format_length(total):
    print('{} feet\n'
          '{} meters\n'
          '{} centimeters'.format(total,
                                  total/3.28084,
                                  (total/3.28084)*100))


def format_area(total):
    print('{} square feet\n'
          '{} square meters\n'
          '{} square centimeters'.format(total,
                                         total/10.7639,
                                         (total/10.7639)*10000))


def format_volume(total):
    print('{} cubic feet\n'
          '{} cubic meters\n'
          '{} cubic centimeters'.format(total,
                                        total/35.3147,
                                        (total/35.3147)*1000000))


formatter_funcs = {ParameterType.Length: format_length,
                   ParameterType.Area: format_area,
                   ParameterType.Volume: format_volume}


def output_param_total(element_list, param_def):
    total_value = calc_param_total(element_list, param_def.name)

    print('Total value for parameter {} is:\n\n'.format(param_def.name))
    if param_def.type in formatter_funcs.keys():
        formatter_funcs[param_def.type](total_value)
    else:
        print('{}\n'.format(total_value))


def process_options(element_list):
    # find all relevant parameters
    shared_params = set()
    shared_type_params = set()

    for el in element_list:
        # find element parameters
        for param in el.ParametersMap:
            if is_calculable_param(param):
                pdef = param.Definition
                shared_params.add(ParamDef(pdef.Name,
                                           pdef.ParameterType))

        # find element type parameters
        el_type = doc.GetElement(el.GetTypeId())
        if el_type and el_type.Id != ElementId.InvalidElementId:
            for type_param in el_type.ParametersMap:
                if is_calculable_param(type_param):
                    pdef = type_param.Definition
                    shared_type_params.add(ParamDef(pdef.Name,
                                                    pdef.ParameterType))

    # make a list of options from discovered parameters
    all_params = shared_params.union(shared_type_params)
    return {'{} <{}>'.format(x.name, x.type):x for x in all_params}


def process_sets(element_list):
    pass

# main -------------------------------------------------------------------------
# ask user to select an option
options = process_options(selection.elements)
selected_switch = \
    CommandSwitchWindow(sorted(options),
                        'Sum values of parameter:').pick_cmd_switch()

if selected_switch:
    output_param_total(selection.elements, options[selected_switch])

    # for type_name, element_set in process_sets(selection.elements):
    #     output_param_total(element_set, options[selected_switch])




# def calc_total_length():
#     lines = []
#     total = 0.0
#
#     print("PROCESSING TOTAL OF {0} OBJECTS:\n\n".format(len(selection)))
#
#     for i, el in enumerate(selection):
#         if isinstance(el, CurveElement):
#             lines.append(el)
#         total += el.LookupParameter('Length').AsDouble()
#     print('TOTAL LENGTH OF ALL SELECTED LINES IS: '
#           '{0} feet / {1} meters'.format(total, _feet_to_meter(total)))
#
#     # group lines per line style
#     linestyles = {}
#     for l in lines:
#         if l.LineStyle.Name in linestyles:
#             linestyles[l.LineStyle.Name].append(l)
#         else:
#             linestyles[l.LineStyle.Name] = [l]
#
#     for k in sorted(linestyles.keys()):
#         linestyletotal = 0.0
#         for l in linestyles[k]:
#             linestyletotal += l.LookupParameter('Length').AsDouble()
#         print("LINES OF STYLE: {0}\nTOTAL LENGTH : {1}\n\n\n".format(k, linestyletotal))
#
#
# def output_area(total):
#     print("TOTAL AREA OF ALL SELECTED ELEMENTS IS:\n"
#           "{0} SQFT\n"
#           "{1} ACRE\n"
#           "{2} SQM".format(total,
#                            total / 43560,
#                            total / 10.7639104))
#
#
