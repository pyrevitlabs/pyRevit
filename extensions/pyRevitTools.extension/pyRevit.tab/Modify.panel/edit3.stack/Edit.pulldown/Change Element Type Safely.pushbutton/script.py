from pyrevit import revit, DB
from pyrevit import script


__context__ = 'selection'
__doc__ = 'Changes element type of the selected elements to a the element '\
          'type of a picked element, while maintaining the values of all '\
          'instance parameters. First select all the elements that you want '\
          'to change the type for and run this tool. '\
          'Then select the element that has the source element type.'


logger = script.get_logger()

exclude_biparams = [DB.BuiltInParameter.ELEM_FAMILY_PARAM, # Family
                   DB.BuiltInParameter.SYMBOL_FAMILY_NAME_PARAM, # Family Name
                   DB.BuiltInParameter.ALL_MODEL_FAMILY_NAME, # Family and Type
                   DB.BuiltInParameter.SYMBOL_FAMILY_AND_TYPE_NAMES_PARAM,
                   DB.BuiltInParameter.ELEM_FAMILY_AND_TYPE_PARAM, 
                   DB.BuiltInParameter.ELEM_TYPE_PARAM, # Type
                   DB.BuiltInParameter.SYMBOL_NAME_PARAM,# Type Name
                   DB.BuiltInParameter.ALL_MODEL_TYPE_NAME,
                   DB.BuiltInParameter.ALL_MODEL_IMAGE] # Image

def get_param_values(element):
    value_dict = {}
    for param in element.Parameters:
        param_name = param.Definition.Name
        if not param.IsReadOnly and param.Definition.BuiltInParameter not in exclude_biparams:
            logger.debug('Getting param value: {}'.format(param_name))
            value_dict[param_name] = revit.db.query.get_param_value(param)
        else:
            logger.debug('Skipping param: {}'.format(param_name))
    return value_dict


def set_param_values(element, value_dict):
    for param in element.Parameters:
        param_name = param.Definition.Name
        if not param.IsReadOnly and param.Definition.BuiltInParameter not in exclude_biparams:
            if param_name in value_dict.keys():
                param_value = value_dict[param_name]
                try:
                    logger.debug('Setting param: {} to value: {}'
                                 .format(param_name, param_value))
                    param.Set(param_value)
                except Exception:
                    logger.debug('Param: {} Value is not settable: {}'
                                 .format(param_name, param_value))


selection = revit.get_selection()
with revit.Transaction('Change Element Types'):
    src_element = \
        revit.pick_element('Pick object with source element type')
    if src_element:
        src_type = src_element.GetTypeId()

        for dest_element in selection.elements:
            logger.debug('Converting: {} | {}'.format(dest_element.Id,
                                                      dest_element))
            value_dict = get_param_values(dest_element)
            new_element = dest_element.ChangeTypeId(src_type)
            if new_element != DB.ElementId.InvalidElementId:
                set_param_values(revit.doc.GetElement(new_element), value_dict)
            else:
                set_param_values(dest_element, value_dict)
