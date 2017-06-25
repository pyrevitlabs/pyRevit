"""
Wall Wrappers

"""  #

import rpw
from rpw import revit, DB
from rpw.db import Element
from rpw.db import Instance, Symbol, Family, Category
from rpw.base import BaseObjectWrapper
from rpw.utils.logger import logger
from rpw.db.builtins import BipEnum


class WallInstance(Instance):
    """
    Inherits base ``Instance`` and overrides symbol attribute to
    get `Symbol` equivalent of Wall `(GetTypeId)`
    """

    _revit_object_category = DB.BuiltInCategory.OST_Walls
    _revit_object_class = DB.Wall
    _collector_params = {'of_class': _revit_object_class, 'is_type': False}

    @property
    def symbol(self):
        wall_type_id = self._revit_object.GetTypeId()
        wall_type = revit.doc.GetElement(wall_type_id)
        return WallSymbol(wall_type)


class WallSymbol(Symbol):
    """
    Inherits from :any:`Symbol` and overrides:
        * :func:`family` to get the `Family` equivalent of Wall `(.Kind)`
        * Uses a different method to get instances.
    """

    _revit_object_class = DB.WallType
    _collector_params = {'of_class': _revit_object_class, 'is_type': True}


    @property
    def family(self):
        """ Returns ``DB.Family`` of the Symbol """
        return WallFamily(self._revit_object.Kind)

    @property
    def instances(self):
        """ Returns all Instances of this Wall Types """
        bip = BipEnum.get_id('SYMBOL_NAME_PARAM')
        param_filter = rpw.db.ParameterFilter(bip, equals=self.name)
        return rpw.db.Collector(parameter_filter=param_filter,
                                **WallInstance._collector_params).elements

    @property
    def siblings(self):
        return self.family.symbols


class WallFamily(Family):
    """
    Inherits base ``Family`` and overrides methods for Wall Instance`
    """

    _revit_object_class = DB.WallKind

    @property
    def symbols(self):
        symbols = rpw.db.Collector(**WallSymbol._collector_params).elements
        return [symbol for symbol in symbols if symbol.Kind == self._revit_object]

    @property
    def category(self):
        wall_type = rpw.db.Collector(of_class=DB.WallType, is_type=True).first
        return WallCategory(wall_type.Category)


class WallCategory(Category):
    """
    ``DB.Category`` Wall Category Wrapper

    Attribute:
        _revit_object (DB.Family): Wrapped ``DB.Category``
    """

    _revit_object_class = DB.Category

    @property
    def families(self):
        """ Returns ``DB.WallKind`` elements in the category """
        wall_kinds = []
        for member in dir(DB.WallKind):
            if type(getattr(DB.WallKind, member)) is DB.WallKind:
                wall_kinds.append(getattr(DB.WallKind, member))
        return wall_kinds
