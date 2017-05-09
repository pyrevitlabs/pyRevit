# noinspection PyUnresolvedReferences
from rpw import DB, doc
from rpw.db.core import BipEnum
from rpw.db.core import Element, Collector, \
                        Instance, Symbol, Family, Category


class Wall(Instance):
    """Inherits base ``Instance`` and overrides symbol attribute to
    get `Symbol` equivalent of Wall `(GetTypeId)`
    """

    _wrapped_class = DB.Wall
    _collector_params = {'of_class': _wrapped_class, 'is_not_type': True}

    def __init__(self, wall_instance, enforce_type=_wrapped_class):
        super(Wall, self).__init__(wall_instance,
                                   enforce_type=enforce_type)

    @property
    def symbol(self):
        wall_type_id = self._wrapped_object.GetTypeId()
        wall_type = doc.GetElement(wall_type_id)
        return Element(wall_type)


class WallSymbol(Symbol):
    """
    Inherits from :any:`Symbol` and overrides:
        * :func:`family` to get the `Family` equivalent of Wall `(.Kind)`
        * Uses a different method to get instances.
    """

    _wrapped_class = DB.WallType
    _collector_params = {'of_class': _wrapped_class, 'is_type': True}

    def __init__(self, wall_symbol, enforce_type=_wrapped_class):
        super(WallSymbol, self).__init__(wall_symbol,
                                         enforce_type=enforce_type)

    @property
    def family(self):
        """ Returns ``DB.Family`` of the Symbol """
        return Element(self._wrapped_object.Kind)

    @property
    def instances(self):
        """ Returns all Instances of this Wall Symbols """
        bip = BipEnum.get_id('SYMBOL_NAME_PARAM')
        param_filter = Collector.ParameterFilter(bip, equals=self.name)
        return Collector(parameter_filter=param_filter,
                         **WallSymbol._collector_params).elements

    @property
    def siblings(self):
        return self.family.symbols


class WallFamily(Family):
    """
    Inherits base ``Family`` and overrides methods for Wall Instance`
    """

    _wrapped_class = DB.WallKind

    def __init__(self, wall_family, enforce_type=_wrapped_class):
        super(WallFamily, self).__init__(wall_family, enforce_type=enforce_type)

    @property
    def symbols(self):
        symbols = Collector(**WallSymbol._collector_params).elements
        return [symbol for symbol in symbols
                if symbol.Kind == self._wrapped_object]

    @property
    def category(self):
        wall_type = Collector(of_class=DB.WallType, is_type=True).first
        return Element(wall_type.Category)


class WallCategory(Category):
    """
    ``DB.Category`` Wall Category Wrapper

    Attribute:
        _revit_object (DB.Family): Wrapped ``DB.Category``
    """

    _wrapped_category = DB.BuiltInCategory.OST_Walls
    _wrapped_class = None

    @property
    def families(self):
        """ Returns ``DB.WallKind`` elements in the category """
        wall_kinds = []
        for member in dir(DB.WallKind):
            if type(getattr(DB.WallKind, member)) is DB.WallKind:
                wall_kinds.append(getattr(DB.WallKind, member))
        return wall_kinds
