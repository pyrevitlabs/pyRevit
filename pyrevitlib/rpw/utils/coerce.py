"""
Type Casting Utilities

"""

import rpw
from rpw import revit, DB
from rpw.base import BaseObjectWrapper
from rpw.db.builtins import BicEnum
from rpw.utils.dotnet import List
from rpw.exceptions import RpwTypeError


def to_element_id(element_reference):
    """
    Coerces Element References (Element, ElementId, ...) to Element Id

    >>> from rpw.utils.coerce import to_element_id
    >>> to_element_id(SomeElement)
    <Element Id>

    """
    if hasattr(element_reference, 'Id'):
        element_id = element_reference.Id
    elif isinstance(element_reference, DB.Reference):
        element_id = element_reference.ElementId
    elif isinstance(element_reference, int):
        element_id = DB.ElementId(element_reference)
    elif isinstance(element_reference, DB.ElementId):
        element_id = element_reference
    elif element_reference == DB.ElementId.InvalidElementId:
        element_id = element_reference
    else:
        raise RpwTypeError('Element, ElementId, or int', type(element_reference))
    return element_id


def to_element_ids(element_references):
    """
    Coerces an element or list of elements into element ids.
    Elements remain unchanged.
    This will always return a list, even if only one element is passed.

    >>> from rpw.utils.coerce import to_element_ids
    >>> to_element_ids(DB.Element)
    [ DB.ElementId ]
    >>> to_element_ids(20001)
    [ DB.ElementId ]
    >>> to_element_ids([20001, 20003])
    [ DB.ElementId, DB.ElementId ]

    Args:
        elements (``DB.Element``): Iterable list (``list`` or ``set``)
                                   or single of ``Element``, ``int``.

    Returns:
        [``DB.ElementId``, ... ]: List of Element Ids.
    """
    element_references = to_iterable(element_references)
    return [to_element_id(e_ref) for e_ref in element_references]

# TODO: Add case to unwrap rpw elements
def to_element(element_reference, doc=revit.doc):
    """ Same as to_elements but for a single object """
    if isinstance(element_reference, DB.Element):
        element = element_reference
    elif isinstance(element_reference, DB.ElementId):
        element = doc.GetElement(element_reference)
    elif isinstance(element_reference, DB.Reference):
        element = doc.GetElement(element_reference)
    elif isinstance(element_reference, int):
        element = doc.GetElement(DB.ElementId(element_reference))
    elif hasattr(element_reference, 'unwrap'):
        element = element_reference.unwrap()
    else:
        raise RpwTypeError('Element, ElementId, or int', type(element_reference))
    return element


def to_elements(element_references, doc=revit.doc):
    """
    Coerces element reference (``int``, or ``ElementId``) into ``DB.Element``.
    Remains unchanged if it's already ``DB.Element``.
    Accepts single object or lists.

    >>> from rpw.utils.coerce import to_elements
    >>> to_elements(DB.ElementId)
    [ DB.Element ]
    >>> to_elements(20001)
    [ DB.Element ]
    >>> to_elements([20001, 20003])
    [ DB.Element, DB.Element ]

    Args:
        element_references ([``DB.ElementId``, ``int``, ``DB.Element``]): Element Reference,
                                                                          single or list

    Returns:
        [``DB.Element``]: Elements
    """
    element_references = to_iterable(element_references)
    return [to_element(e_ref) for e_ref in element_references]


def to_class(class_reference):
    """ Coerces a class or class reference to a Class.

    >>> from rpw.utils.coerce import to_class
    >>> to_class('Wall')
    [ DB.Wall ]
    >>> to_class(Wall)
    [ DB.Wall ]

    Args:
        class_reference ([``DB.Wall``, ``str``]): Class Reference or class name

    Returns:
        [``type``]: Class
    """
    if isinstance(class_reference, str):
        return getattr(DB, class_reference)
    if isinstance(class_reference, type):
        return class_reference
    raise RpwTypeError('Class Type, Class Type Name', type(class_reference))


def to_category(category_reference, fuzzy=True):
    """ Coerces a category, category name or category id to a BuiltInCategory.

    >>> from rpw.utils.coerce import to_category
    >>> to_category('OST_Walls')
    BuiltInCategory.OST_Walls
    >>> to_category('Walls')
    BuiltInCategory.OST_Walls
    >>> to_category(BuiltInCategory.OST_Walls)
    BuiltInCategory.OST_Walls

    Args:
        cateagory_reference ([``DB.BuiltInCategory``, ``str``, ``CategoryId``]): Category Reference
                                                                                 or Name

    Returns:
        [``BuiltInCategory``]: BuiltInCategory
    """
    if isinstance(category_reference, DB.BuiltInCategory):
        return category_reference
    if isinstance(category_reference, str):
        if fuzzy:
            return BicEnum.fuzzy_get(category_reference)
        else:
            return BicEnum.get(category_reference)
    if isinstance(category_reference, DB.ElementId):
        return BicEnum.from_category_id(category_reference)
    raise RpwTypeError('Category Type, Category Type Name',
                       type(category_reference))


def to_category_id(category_reference, fuzzy=True):
    """
    Coerces a category, category name or category id to a Category Id.

    >>> from rpw.utils.coerce import to_category_id
    >>> to_category_id('OST_Walls')
    <ElementId>
    >>> to_category_id('Wall')
    <ElementId>
    >>> to_category_id(BuiltInCategory.OST_Walls)
    <ElementId>

    Args:
        cateagory_reference ([``DB.BuiltInCategory``, ``str``, ``CategoryId``]): Category Reference
                                                                                 or Name

    Returns:
        [``DB.ElementId``]: ElementId of Category
    """
    category_enum = to_category(category_reference)
    return DB.ElementId(category_enum)


def to_iterable(item_or_iterable):
    """
    Ensures input is iterable

    >>> from rpw.utils.coerce import to_iterable
    >>> to_iterable(SomeElement)
    [SomeElement]

    Args:
        any (iterable, non-iterable)

    Returns:
        (`iterable`): Same as input
    """
    if hasattr(item_or_iterable, '__iter__'):
        return item_or_iterable
    else:
        return [item_or_iterable]


def to_pascal_case(snake_str):
    """ Converts Snake Case to Pascal Case

    >>> to_pascal_case('family_name')
    'FamilyName'
    """
    components = snake_str.split('_')
    return "".join(x.title() for x in components)


# def dictioary_to_string(dictionary):
#     """ Makes a string with key:value pairs from a dictionary

#     >>> dictionary_to_string({'name': 'value'})
#     'name:value'
#     >>> dictionary_to_string({'name': 'value', 'id':5})
#     'name:value id:5'
#     """
#     return ' '.join(['{0}:{1}'.format(k, v) for k, v in dictionary.iteritems()])
