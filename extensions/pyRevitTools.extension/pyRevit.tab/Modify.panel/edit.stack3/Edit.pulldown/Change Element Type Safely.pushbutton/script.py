from revitutils import doc, uidoc, selection

# noinspection PyUnresolvedReferences
from Autodesk.Revit.DB import Transaction, ElementId, StorageType


__doc__ = 'Changes element type of the selected elements to a the element type of a picked element, '\
          'while maintaining the values of all instance parameters. First select all the elements that you want '\
          'to change the type for and run this tool. Then select the element that has the source element type.'

exclude_params = ['Family', 'Family and Type', 'Type', 'Type Name']


def get_param_values(element):
    value_dict = {}
    for param in element.Parameters:
        param_name = param.Definition.Name
        if not param.IsReadOnly and param_name not in exclude_params:
            if param.StorageType == StorageType.Integer:
                value_dict[param_name] = param.AsInteger()
            elif param.StorageType == StorageType.Double:
                value_dict[param_name] = param.AsDouble()
            elif param.StorageType == StorageType.String:
                value_dict[param_name] = param.AsString()
            elif param.StorageType == StorageType.ElementId:
                value_dict[param_name] = param.AsElementId()

    return value_dict


def set_param_values(element, value_dict):
    for param in element.Parameters:
        param_name = param.Definition.Name
        if not param.IsReadOnly and param_name not in exclude_params:
            if param_name in value_dict.keys():
                param.Set(value_dict[param_name])


with Transaction(doc, 'Change Element Types') as t:
    t.Start()
    src_element = selection.utils.pick_element('Pick object with source element type')
    if src_element:
        src_type = src_element.GetTypeId()

        for dest_element in selection.elements:
            value_dict = get_param_values(dest_element)
            new_element = dest_element.ChangeTypeId(src_type)
            if new_element != ElementId.InvalidElementId:
                set_param_values(doc.GetElement(new_element), value_dict)
            else:
                set_param_values(dest_element, value_dict)
    t.Commit()
