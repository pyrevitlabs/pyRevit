"""Wrappers for Builtin Enums

>>> BipEnum.get('WALL_LOCATION_LINE')
Revit.DB.BuiltInParameter.WALL_LOCATION_LINE
>>> BipEnum.get_id('WALL_LOCATION_LINE')
Revit.DB.ElementId

"""

# noinspection PyUnresolvedReferences
from rpw import DB, BaseEnumWrapper

import clr
clr.AddReference('System')
# noinspection PyUnresolvedReferences
from System import Enum


class BuiltinCategoryEnumWrapper(BaseEnumWrapper):
    """BuiltInCategory Enum Wrapper

    """

    def __init__(self):
        super(BaseEnumWrapper, self).__init__()
        self._api_enum = DB.BuiltInCategory

    def from_category_id(self, category_id):
        """Casts ``DB.BuiltInCategory`` Enum member from a Category ElementId

        Args:
            category_id (``DB.ElementId``): ElementId of a Category

        Returns:
            ``DB.BuiltInCategory`` member

        """

        return Enum.ToObject(self._api_enum, category_id.IntegerValue)
        # Similar to: Category.GetCategory(doc, category.Id).Name


BipEnum = BaseEnumWrapper(DB.BuiltInParameter)
BicEnum = BuiltinCategoryEnumWrapper()
