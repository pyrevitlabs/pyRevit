from pyrevit import revit, DB
from pyrevit import script


__context__ = 'selection'
__doc__ = 'Changes element type of the selected elements to a the element '\
          'type of a picked element, while maintaining the values of all '\
          'instance parameters. First select all the elements that you want '\
          'to change the type for and run this tool. '\
          'Then select the element that has the source element type.'


logger = script.get_logger()


exclude_params = ['Family', 'Family Name', 'Family and Type',
                  'Type', 'Type Name', 'Image']


def get_param_values(element):
    value_dict = {}
    for param in element.Parameters:
        param_name = param.Definition.Name
        if not param.IsReadOnly and param_name not in exclude_params:
            logger.debug('Getting param value: {}'.format(param_name))
            if param.StorageType == DB.StorageType.Integer:
                value_dict[param_name] = param.AsInteger()
                logger.debug('Param value is Integer: {}'
                             .format(value_dict[param_name]))

            elif param.StorageType == DB.StorageType.Double:
                value_dict[param_name] = param.AsDouble()
                logger.debug('Param value is Double: {}'
                             .format(value_dict[param_name]))

            elif param.StorageType == DB.StorageType.String:
                value_dict[param_name] = param.AsString()
                logger.debug('Param value is String: {}'
                             .format(value_dict[param_name]))

            elif param.StorageType == DB.StorageType.ElementId:
                value_dict[param_name] = param.AsElementId()
                logger.debug('Param value is ElementId: {}'
                             .format(value_dict[param_name]))
        else:
            logger.debug('Skipping param: {}'.format(param_name))

    return value_dict


def set_param_values(element, value_dict):
    for param in element.Parameters:
        param_name = param.Definition.Name
        if not param.IsReadOnly and param_name not in exclude_params:
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
