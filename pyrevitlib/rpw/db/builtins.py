"""

>>> BipEnum.get('WALL_LOCATION_LINE')
Revit.DB.BuiltInParameter.WALL_LOCATION_LINE
>>> BipEnum.get_id('WALL_LOCATION_LINE')
Revit.DB.ElementId

Note:
    These classes were originally create to be used internally,
    but are documented here as some its functionalities could be
    helpful to others.

----------------------------------------------------------------
"""

###
import re
from rpw import revit, DB
from rpw.base import BaseObject, BaseObjectWrapper
from rpw.utils.dotnet import Enum
from rpw.exceptions import RpwCoerceError


class _BiParameter(BaseObjectWrapper):
    """
    BuiltInParameter Wrapper

    >>> BiParameter.get('WALL_LOCATION_LINE')
    Revit.DB.BuiltInParameter.WALL_LOCATION_LINE
    >>> BiParameter.get_id('WALL_LOCATION_LINE')
    Revit.DB.ElementId
    """

    _revit_object_class = DB.BuiltInParameter

    def __init__(self):
        super(_BiParameter, self).__init__(DB.BuiltInParameter,
                                          enforce_type=False)

    def __getattr__(self, attr):
        return self.get(attr)

    def get(self, parameter_name):
        """ Gets Built In Parameter by Name

        Args:
            ``str``: Name of Parameter

        Returns:
            ``DB.BuiltInParameter``: BuiltInParameter Enumeration Member

        """
        try:
            enum = getattr(DB.BuiltInParameter, parameter_name)
        except AttributeError:
            raise RpwCoerceError(parameter_name, DB.BuiltInParameter)
        return enum

    def get_id(self, parameter_name):
        """ Gets ElementId of Category by name

        Args:
            parameter_name(``str``): Name of Built In Parameter

        Returns:
            ``DB.BuitInParameter``: BuiltInParameter Enumeration Member
        """
        enum = self.get(parameter_name)
        return DB.ElementId(enum)


class _BiCategory(BaseObjectWrapper):
    """
    Enumeration Wrapper

    >>> BiCategory.get('OST_Rooms')
    Revit.DB.BuiltInCategory.OST_Rooms
    >>> BiCategory.get_id('OST_Rooms')
    Revit.DB.ElementId
    >>> BiCategory.from_category_id(furniture.Category.Id)
    DB.BuiltInCategory.OST_Furniture
    """

    _revit_object_class = DB.BuiltInCategory

    def __init__(self):
        super(_BiCategory, self).__init__(DB.BuiltInCategory,
                                         enforce_type=False)

    def get(self, category_name):
        """ Gets Built In Category by Name

        Args:
            ``str``: Name of Category

        Returns:
            ``DB.BuiltInCategory``: BuiltInCategory Enumeration Member
        """

        try:
            enum = getattr(DB.BuiltInCategory, category_name)
        except AttributeError:
            raise RpwCoerceError(category_name, DB.BuiltInCategory)
        return enum

    def fuzzy_get(self, loose_category_name):
        loose_category_name = loose_category_name.replace(' ', '').lower()
        loose_category_name = loose_category_name.replace('ost_', '')
        for category_name in dir(DB.BuiltInCategory):
            exp = '(OST_)({})$'.format(loose_category_name)
            if re.search(exp, category_name, re.IGNORECASE):
                return self.get(category_name)
        # If not Found Try regular method, handle error
        return self.get(loose_category_name)


    def get_id(self, category_name):
        """ Gets ElementId of Category by name

        Args:
            ``str``: Name of Category

        Returns:
            ``DB.BuiltInCategory``: BuiltInCategory Enumeration Member
        """
        enum = self.get(category_name)
        return DB.ElementId(enum)

    def from_category_id(self, category_id):
        """
        Casts ``DB.BuiltInCategory`` Enumeration member from a Category ElementId

        Args:
            category_id (``DB.ElementId``): ElementId reference of a category

        Returns:
            ``DB.BuiltInCategory`` member
        """
        return Enum.ToObject(DB.BuiltInCategory, category_id.IntegerValue)
        # Similar to: Category.GetCategory(doc, category.Id).Name

# Classes should already be instantiated
BiParameter = _BiParameter()
BiCategory = _BiCategory()
# TODO: Replace on Tests and Code!
BipEnum = BiParameter
BicEnum = BiCategory
