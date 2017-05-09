# noinspection PyUnresolvedReferences
from rpw import DB, doc, RpwTypeError


def to_element_ids(mixed_list):
    if not isinstance(mixed_list, list) and not isinstance(mixed_list, set):
        mixed_list = [mixed_list]

    element_ids = []
    for item in mixed_list:
        if isinstance(item, DB.Element):
            element_ids.append(item.Id)
        elif isinstance(item, int):
            element_ids.append(DB.ElementId(item))
        elif isinstance(item, DB.ElementId):
            element_ids.append(item)
        elif isinstance(item, DB.ElementId.InvalidElementId):
            element_ids.append(item)
        else:
            raise RpwTypeError('Element, ElementId, or int', type(item))

    return element_ids


def to_elements(mixed_list):
    if not isinstance(mixed_list, list):
        mixed_list = [mixed_list]

    elements = []

    for item in mixed_list:

        if isinstance(item, DB.ElementId):
            element = doc.GetElement(item)

        elif isinstance(item, int):
            element = doc.GetElement(DB.ElementId(item))

        elif isinstance(item, DB.Element):
            element = item

        else:
            raise RpwTypeError('Element, ElementId, or int',
                               type(item))

        elements.append(element)

    return elements
