from scriptutils.userinput import CommandSwitchWindow
from revitutils import doc, selection

# noinspection PyUnresolvedReferences
from Autodesk.Revit.DB import CurveElement, ElementId, StorageType

__doc__ = 'Sums up the values of selected parameter on selected elements. This tool studies the selected ' \
          'elements and their associated types and presents the user with a list of parameters that are ' \
          'shared between the selected elements. Only parameters with Double or Interger values are included.'
          
__title__ = 'Sum Total'


def _is_calculable_param(param):
    if param.StorageType == StorageType.Double:
        return True

    if param.StorageType == StorageType.Integer:
        val_str = param.AsValueString()
        if val_str and unicode(val_str).lower().isdigit():
            return True

    return False


def _add_total(total, param):
    if param.StorageType == StorageType.Double:
        total += param.AsDouble()
    elif param.StorageType == StorageType.Integer:
        total += param.AsInteger()

    return total


def _calc_param_total(param_name):
    total = 0.0
    for el in selection.elements:
        param = el.LookupParameter(param_name)
        if not param:
            el_type = doc.GetElement(el.GetTypeId())
            type_param = el_type.LookupParameter(param_name)
            if not type_param:
                print('Elemend with ID: {} does not have {} parameter.'.format(el.Id, param_name))
            else:
                total = _add_total(total, type_param)
        else:
            total = _add_total(total, param)

    return total


def calc_total_length():
    lines = []
    total = 0.0

    print("PROCESSING TOTAL OF {0} OBJECTS:\n\n".format(len(selection)))

    for i, el in enumerate(selection):
        if isinstance(el, CurveElement):
            lines.append(el)
        total += el.LookupParameter('Length').AsDouble()
    print("TOTAL LENGTH OF ALL SELECTED LINES IS: {0}\n\n\n".format(total))

    # group lines per line style
    linestyles = {}
    for l in lines:
        if l.LineStyle.Name in linestyles:
            linestyles[l.LineStyle.Name].append(l)
        else:
            linestyles[l.LineStyle.Name] = [l]

    for k in sorted(linestyles.keys()):
        linestyletotal = 0.0
        for l in linestyles[k]:
            linestyletotal += l.LookupParameter('Length').AsDouble()
        print("LINES OF STYLE: {0}\nTOTAL LENGTH : {1}\n\n\n".format(k, linestyletotal))


def output_area(total):
    print("TOTAL AREA OF ALL SELECTED ELEMENTS IS:\n{0} SQFT\n{1} ACRE".format(total, total / 43560))


custom_calc_funcs = {'Length': calc_total_length}
custom_output_formatters = {'Area': output_area}


# find all relevant parameters
shared_params = set()
shared_type_params = set()

for el in selection:
    for param in el.ParametersMap:
        if _is_calculable_param(param):
            shared_params.add(param.Definition.Name)

    el_type = doc.GetElement(el.GetTypeId())
    if el_type and el_type.Id != ElementId.InvalidElementId:
        for type_param in el_type.ParametersMap:
            if _is_calculable_param(type_param):
                shared_type_params.add(type_param.Definition.Name)


# make a list of options from discovered parameters
options = list(shared_params.union(shared_type_params))
# options.extend(custom_calc_funcs.keys())

# ask user to select an option
selected_switch = CommandSwitchWindow(sorted(options), 'Sum values of parameter:').pick_cmd_switch()

total = 0

# process selection option and get the calculated total
if selected_switch:
    if selected_switch in custom_calc_funcs:
        total = custom_calc_funcs[selected_switch]()
    else:
        total = _calc_param_total(selected_switch)

    # figure out how to output the total
    if selected_switch in custom_output_formatters:
        custom_output_formatters[selected_switch](total)
    else:
        print("TOTAL {} OF ALL SELECTED ELEMENTS IS: {}".format(selected_switch.upper(), total))
