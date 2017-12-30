"""
Wall Wrappers

"""  #

import rpw
from rpw import revit, DB
from rpw.db import Element
from rpw.db import FamilyInstance, FamilySymbol, Family, Category
from rpw.base import BaseObjectWrapper
from rpw.utils.logger import logger, deprecate_warning
from rpw.utils.coerce import to_element_id
from rpw.db.builtins import BipEnum
from rpw.exceptions import RpwTypeError, RpwCoerceError
from rpw.utils.mixins import ByNameCollectMixin


class Wall(FamilyInstance):
    """
    Inherits base ``FamilyInstance`` and overrides symbol attribute to
    get `Symbol` equivalent of Wall - WallType `(GetTypeId)`
    """

    _revit_object_category = DB.BuiltInCategory.OST_Walls
    _revit_object_class = DB.Wall
    _collector_params = {'of_class': _revit_object_class, 'is_type': False}

    def change_type(self, wall_type_reference):
        """
        Change Wall Type

        Args:
            wall_type_reference (``ElementId``, ``WallType``, ``str``): Wall Type Reference
        """
        wall_type = WallType.by_name_or_element_ref(wall_type_reference)
        wall_type_id = to_element_id(wall_type)
        self._revit_object.ChangeTypeId(wall_type_id)

    def get_symbol(self, wrapped=True):
        """ Get Wall Type Alias """
        return self.get_wall_type(wrapped)

    @property
    def symbol(self):
        deprecate_warning('Wall.symbol', 'Wall.get_symbol()')
        return self.get_symbol(wrapped=True)

    def get_wall_type(self, wrapped=True):
        """ Get Wall Type """
        wall_type_id = self._revit_object.GetTypeId()
        wall_type = self.doc.GetElement(wall_type_id)
        return WallType(wall_type) if wrapped else wall_type

    @property
    def wall_type(self):
        deprecate_warning('Wall.wall_type', 'Wall.get_wall_type()')
        return self.get_wall_type(wrapped=True)

    def get_wall_kind(self, wrapped=True):
        wall_type = self.get_wall_type(wrapped=True)
        return wall_type.get_wall_kind(wrapped=wrapped)

    @property
    def wall_kind(self):
        deprecate_warning('Wall.wall_kind', 'Wall.get_wall_kind()')
        return self.get_wall_kind(wrapped=True)

    def get_family(self, wrapped=True):
        """ Get WallKind Alias """
        return self.get_wall_kind(wrapped=wrapped)

    @property
    def family(self):
        deprecate_warning('Wall.family', 'Wall.get_family()')
        return self.get_family(wrapped=True)

    def get_category(self, wrapped=True):
        """ Get Wall Category """
        return WallCategory(self._revit_object.Category)

    @property
    def category(self):
        """ Wrapped ``DB.Category`` of the ``DB.Wall`` """
        deprecate_warning('Wall.category', 'Wall.get_category()')
        return self.get_category(wrapped=True)


class WallType(FamilySymbol, ByNameCollectMixin):
    """
    Inherits from :any:`FamilySymbol` and overrides:
        * :func:`wall_kind` to get the `Family` equivalent of Wall `(.Kind)`
        * Uses a different method to get instances.
    """

    _revit_object_class = DB.WallType
    _collector_params = {'of_class': _revit_object_class, 'is_type': True}

    def get_family(self, wrapped=True):
        return self.get_wall_kind(wrapped=wrapped)

    @property
    def family(self):
        deprecate_warning('WallType.family', 'WallType.get_family()')
        return self.get_wall_kind(wrapped=True)

    def get_wall_kind(self, wrapped=True):
        """ Returns ``DB.Family`` of the Symbol """
        kind = self._revit_object.Kind
        return WallKind(kind) if wrapped else kind

    @property
    def wall_kind(self):
        """ Returns ``DB.Family`` of the Symbol """
        deprecate_warning('WallType.wall_kind', 'WallType.get_wall_kind()')
        return self.get_wall_kind(wrapped=True)

    def get_instances(self, wrapped=True):
        """ Returns all Instances of this Wall Types """
        bip = BipEnum.get_id('SYMBOL_NAME_PARAM')
        param_filter = rpw.db.ParameterFilter(bip, equals=self.name)
        return rpw.db.Collector(parameter_filter=param_filter,
                                **Wall._collector_params).wrapped_elements

    @property
    def instances(self):
        """ Returns all Instances of this Wall Types """
        deprecate_warning('WallType.instances', 'WallType.get_instances()')
        return self.get_instances(wrapped=True)

    def get_siblings(self, wrapped=True):
        wall_kind = self.get_wall_kind(wrapped=True)
        return wall_kind.get_wall_types(wrapped=wrapped)

    @property
    def siblings(self):
        deprecate_warning('WallType.siblings', 'WallType.get_siblings()')
        return self.get_siblings(wrapped=True)

    def get_category(self, wrapped=True):
        """ Get Wall Category """
        return WallCategory(self._revit_object.Category)

    @property
    def category(self):
        """ Wrapped ``DB.Category`` of the ``DB.Wall`` """
        deprecate_warning('Wall.category', 'Wall.get_category()')
        return self.get_category(wrapped=True)


# class WallKind(Family):
class WallKind(BaseObjectWrapper):
    """
    Equivalent of ``Family`` but is Enumerator for Walls.

    Can be Basic, Stacked, Curtain, Unknown
    """

    _revit_object_class = DB.WallKind

    @property
    def name(self):
        """ Retuns Pretty Name as shown on UI: Basic > Basic Wall """
        # Same method as Family Works, but requires Code duplication
        # Since this should not inherit from Family.
        # Solution copy code or Mixin. Or return Enum Name:  'Basic'
        # This works but requires Lookup.
        # wall_type = self.get_wall_types()[0]
        # return wall_type.parameters.builtins['SYMBOL_FAMILY_NAME_PARAM'].value
        # return '{} Wall'.format(self._revit_object.ToString())
        return self._revit_object.ToString()

    def get_symbols(self, wrapped=True):
        """ Get Wall Types Alias """
        return self.get_wall_types(wrapped=wrapped)

    @property
    def symbols(self):
        deprecate_warning('WallKind.symbols', 'WallKind.get_symbols()')
        return self.get_symbols(wrapped=True)

    def get_wall_types(self, wrapped=True):
        """ Get Wall Types Alias """
        type_collector = rpw.db.WallType.collect()
        wall_types = type_collector.get_elements(wrapped=wrapped)
        return [wall_type for wall_type in wall_types
                if wall_type.Kind == self._revit_object]

    @property
    def wall_types(self):
        deprecate_warning('WallKind.wall_types', 'WallKind.get_wall_types()')
        return self.get_wall_types(wrapped=True)

    def get_instances(self, wrapped=True):
        """ Returns all Wall instances of this given Wall Kind"""
        instances = []
        for wall_type in self.get_wall_types(wrapped=True):
            instances.extend(wall_type.get_instances(wrapped=wrapped))
        return instances

    @property
    def instances(self):
        """ Returns all Wall instances of this given Wall Kind"""
        deprecate_warning('WallKind.instances', 'WallKind.get_instances()')
        return self.get_instances(wrapped=True)

    def get_category(self, wrapped=True):
        cat = DB.Category.GetCategory(revit.doc, DB.BuiltInCategory.OST_Walls)
        return WallCategory(cat) if wrapped else cat

    @property
    def category(self):
        deprecate_warning('WallKind.category', 'WallKind.get_category()')
        return self.get_category(wrapped=True)

    def __repr__(self):
        return super(WallKind, self).__repr__({'name': self.name})

class WallCategory(Category):
    """
    ``DB.Category`` Wall Category Wrapper

    Attribute:
        _revit_object (DB.Family): Wrapped ``DB.Category``
    """

    _revit_object_class = DB.Category

    def get_families(self, wrapped=True):
        """ Returns ``DB.WallKind`` elements in the category """
        wall_kinds = []
        for member in dir(DB.WallKind):
            if type(getattr(DB.WallKind, member)) is DB.WallKind:
                wall_kind = getattr(DB.WallKind, member)
                wall_kind = WallKind(wall_kind) if wrapped else wall_kind
                wall_kinds.append(wall_kind)
        return wall_kinds

    @property
    def families(self):
        """ Returns ``DB.WallKind`` elements in the category """
        deprecate_warning('WallCategory.families',
                          'WallCategory.get_families()')
        return self.get_families(wrapped=True)
