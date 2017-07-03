"""
Element Model Wrappers provide a consitent interface for acccessing parameters and properties
of commonly used elements.

"""  #

import inspect

import rpw
from rpw import revit, DB
from rpw.db.parameter import Parameter, ParameterSet
from rpw.base import BaseObjectWrapper
from rpw.exceptions import RpwException, RpwWrongStorageType
from rpw.exceptions import RpwParameterNotFound, RpwTypeError
from rpw.utils.logger import logger
from rpw.db.builtins import BicEnum, BipEnum


class Element(BaseObjectWrapper):
    """
    Inheriting from element extends wrapped elements with a new :class:`parameters`
    attribute, well as the :func:`unwrap` method inherited from the :any:`BaseObjectWrapper` class.

    It can be created by instantiating ``rpw.db.Element`` , or one of the helper
    static methods shown below.

    Most importantly, all other `Element-related` classes inhert from this class
    so it can provide parameter access.

    >>> element = rpw.db.Element(SomeElement)
    >>> element = rpw.db.Element.from_id(ElementId)
    >>> element = rpw.db.Element.from_int(Integer)

    >>> wall = rpw.db.Element(RevitWallElement)
    >>> wall.Id
    >>> wall.parameters['Height'].value
    10.0

    The ``Element`` Constructor can be used witout specifying the
    exact class. On instantiation, it will attempt to map the type provided,
    if a match is not found, an Element will be used.
    If the element does not inherit from DB.Element, and exception is raised.

    >>> wall_instance = rpw.db.Element(SomeWallInstance)
    >>> type(wall_instance)
    'rpw.db.WallInstance'
    >>> wall_symbol = rpw.db.Element(SomeWallSymbol)
    >>> type(wall_symbol)
    'rpw.db.WallSymbol'

    Attributes:

        parameters (:any:`ParameterSet`): Access :any:`ParameterSet` class.
        parameters.builtins (:any:`ParameterSet`): BuitIn :any:`ParameterSet` object

    Methods:
        unwrap(): Wrapped Revit Reference

    """

    _revit_object_class = DB.Element

    def __new__(cls, element, **kwargs):
        """
        Factory Constructor will chose the best Class for the Element.
        This function iterates through all classes in the rpw.db module,
        and will find one that wraps the corresponding class. If and exact
        match is not found :any:`Element` is used
        """
        defined_wrapper_classes = inspect.getmembers(rpw.db, inspect.isclass)
        # [('Area', '<class Area>'), ... ]

        _revit_object_class = cls._revit_object_class

        if element is None:
            raise RpwTypeError('Element or Element Child', 'None')

        # Ensure Wrapped Element is instance of Class Wrapper or decendent
        # Must also check is element because isinstance(Element, Element) is False
        if not isinstance(element, _revit_object_class):
        #    or cls is not Element:
            raise RpwTypeError(_revit_object_class, type(element))

        # rpw.ui.forms.Console()
        for class_name, wrapper_class in defined_wrapper_classes:
            if type(element) is getattr(wrapper_class, '_revit_object_class', None):
                # Found Mathing Class, Use Wrapper
                # print('Found Mathing Class, Use Wrapper: {}'.format(class_name))
                return super(Element, cls).__new__(wrapper_class, element, **kwargs)
                # new_obj._revit_object = element
                # return new_object
        else:
            # Could Not find a Matching Class, Use Element if related
            # print('Did not find a Matching Class, will use Element if related')
            if DB.Element in inspect.getmro(element.__class__):
                return super(Element, cls).__new__(cls, element, **kwargs)
        element_class_name = element.__class__.__name__
        raise RpwException('Factory does not support type: {}'.format(element_class_name))

    def __init__(self, element, doc=revit.doc):
        """
        Main Element Instantiation

        >>> wall = rpw.db.Element(SomeElementId)
        <rpw: WallInstance % DB.Wall >
        >>> wall.parameters['Height']
        10.0
        >>> wall.parameters.builtins['WALL_LOCATION_LINE']
        1

        Args:
            element (`Element Reference`): Can be ``DB.Element``, ``DB.ElementId``, or ``int``.

        Returns:
            :class:`Element`: Instance of Wrapped Element.

        """

        super(Element, self).__init__(element)
        self.doc = doc
        if isinstance(element, DB.Element):
            # WallKind Inherits from Family/Element, but is not Element,
            # so ParameterSet fails. Parameters are only added if Element
            # inherits from element
            self.parameters = ParameterSet(element)

    @classmethod
    def collect(cls, **kwargs):
        """ Collect all elements of the wrapper, using the default collector.

        Collector will use default params for that Element (ie: Room ``{'of_category': 'OST_rooms'}``).
        These can be overriden by passing keyword args to the collectors call.

        >>> rooms = rpw.Rooms.collect()
        [<rpw:Room % DB.Room | Room:1>]
        >>> rooms = rpw.Area.collect()
        [<rpw:Area % DB.Area | Rentable:30.2>]
        >>> rooms = rpw.WallInstance.collect(level="Level 1")
        [<rpw:WallInstance % DB.Wall symbol:Basic Wall>]

        """
        _collector_params = getattr(cls, '_collector_params', None)

        if _collector_params:
            kwargs.update(_collector_params)
            return rpw.db.Collector(**kwargs)
        else:
            raise RpwException('Wrapper cannot collect by class: {}'.format(cls.__name__))

    @staticmethod
    def from_int(id_int):
        """ Instantiate Element from an Integer representing and Id """
        element = revit.doc.GetElement(DB.ElementId(id_int))
        return Element(element)

    @staticmethod
    def from_id(element_id):
        """ Instantiate Element from an ElementId """
        element = revit.doc.GetElement(element_id)
        return Element(element)

    @staticmethod
    def Factory(element):
        # Depracated - For Compatibility Only
        msg = 'Element.Factory() has been depracated. Use Element()'
        logger.warning(msg)
        return Element(element)

    def delete(self):
        """ Deletes Element from Model """
        self.doc.Delete(self._revit_object.Id)

    def __repr__(self, data=None):
        if data is None:
            data = {}
        element_id = getattr(self._revit_object, 'Id', None)
        if element_id:
            data.update({'id': element_id})
        return super(Element, self).__repr__(data=data)


class FamilyInstance(Element):
    """
    `DB.FamilyInstance` Wrapper

    >>> instance = rpw.db.Element(SomeFamilyInstance)
    <rpw:FamilyInstance % DB.FamilyInstance | name:72" x 36">
    >>> instance.symbol.name
    '72" x 36"'
    >>> instance.family
    <RPW_Family:desk>
    >>> instance.siblings
    [<rpw:FamilyInstance % DB.FamilyInstance | name:72" x 36">, ... ]

    Attribute:
        _revit_object (DB.FamilyInstance): Wrapped ``DB.FamilyInstance``
    """

    _revit_object_class = DB.FamilyInstance
    _collector_params = {'of_class': _revit_object_class, 'is_not_type': True}

    @property
    def symbol(self):
        """ Wrapped ``DB.FamilySymbol`` of the ``DB.FamilyInstance`` """
        symbol = self._revit_object.Symbol
        return FamilySymbol(symbol)

    @property
    def family(self):
        """ Wrapped ``DB.Family`` of the ``DB.FamilyInstance`` """
        return self.symbol.family

    @property
    def category(self):
        """ Wrapped ``DB.Category`` of the ``DB.Symbol`` """
        return self.family.category

    @property
    def siblings(self):
        """ Other ``DB.FamilyInstance`` of the same ``DB.FamilySymbol`` """
        return self.symbol.instances

    def __repr__(self):
        return super(FamilyInstance, self).__repr__(data={'symbol': self.symbol.name})


class FamilySymbol(Element):
    """
    `DB.FamilySymbol` Wrapper

    >>> symbol = rpw.db.Element(SomeSymbol)
    <rpw:FamilySymbol % DB.FamilySymbol | name:72" x 36">
    >>> instance.symbol.name
    '72" x 36"'
    >>> instance.family
    <rpw:Family % DB.Family | name:desk>
    >>> instance.siblings
    <rpw:Family % DB.Family | name:desk>, ... ]

    Attribute:
        _revit_object (DB.FamilySymbol): Wrapped ``DB.FamilySymbol``
    """
    _revit_object_class = DB.FamilySymbol
    _collector_params = {'of_class': _revit_object_class, 'is_type': True}

    @property
    def name(self):
        #TODO: Add setter - maybe as a mixin
        """ Returns the name of the Symbol """
        return self.parameters.builtins['SYMBOL_NAME_PARAM'].value
        # return self.parameters.builtins['ALL_MODEL_TYPE_NAME'].value

    @property
    def family(self):
        """Returns:
            :any:`Family`: Wrapped ``DB.Family`` of the symbol """
        return Family(self._revit_object.Family)

    @property
    def instances(self):
        """Returns:
            [``DB.FamilyInstance``]: List of model instances of the symbol (unwrapped)
        """
        return rpw.db.Collector(symbol=self._revit_object.Id, is_not_type=True).elements

    @property
    def siblings(self):
        """Returns:
            [``DB.FamilySymbol``]: List of symbol Types of the same Family (unwrapped)
        """
        symbols_ids = self._revit_object.GetSimilarTypes()
        return [revit.doc.GetElement(i) for i in symbols_ids]
        # Same as: return self.family.symbols

    @property
    def category(self):
        """Returns:
        :any:`Category`: Wrapped ``DB.Category`` of the symbol """
        return self.family.category

    def __repr__(self):
        return super(FamilySymbol, self).__repr__(data={'name': self.name})


class Family(Element):
    """
    `DB.Family` Wrapper

    Attribute:
        _revit_object (DB.Family): Wrapped ``DB.Family``
    """

    _revit_object_class = DB.Family
    _collector_params = {'of_class': _revit_object_class}

    @property
    def name(self):
        """ Returns:
            ``str``: name of the Family """
        # This BIP only exist in symbols, so we retrieve a symbol first.
        # The Alternative is to use Element.Name.GetValue(), but I am
        # avoiding it due to the import bug in ironpython
        # https://github.com/IronLanguages/ironpython2/issues/79
        try:
            symbol = self.symbols[0]
        except IndexError:
            raise RpwException('Family [{}] has no symbols'.format(self.name))
        return Element(symbol).parameters.builtins['SYMBOL_FAMILY_NAME_PARAM'].value
        # Uses generic factory so it can be inherited by others
        # Alternative: ALL_MODEL_FAMILY_NAME

    @property
    def instances(self):
        """Returns:
            [``DB.FamilyInstance``]: List of model instances in this family (unwrapped)
        """
        # There has to be a better way
        instances = []
        for symbol in self.symbols:
            symbol_instances = Element(symbol).instances
            instances.append(symbol_instances)
        return instances

    @property
    def symbols(self):
        """Returns:
            [``DB.FamilySymbol``]: List of Symbol Types in the family (unwrapped)
        """
        symbols_ids = self._revit_object.GetFamilySymbolIds()
        return [revit.doc.GetElement(i) for i in symbols_ids]

    @property
    def category(self):
        """Returns:
            :any:`Category`: Wrapped ``DB.Category`` of the Family """
        return Category(self._revit_object.FamilyCategory)

    @property
    def siblings(self):
        """Returns:
            [``DB.Family``]: List of Family elements in the same category (unwrapped)
        """
        return self.category.families

    def __repr__(self):
        return super(Family, self).__repr__({'name': self.name})


class Category(BaseObjectWrapper):
    """
    `DB.Category` Wrapper

    Attribute:
        _revit_object (DB.Family): Wrapped ``DB.Category``
    """

    _revit_object_class = DB.Category

    @property
    def name(self):
        """ Returns name of the Category """
        return self._revit_object.Name

    @property
    def families(self):
        """Returns:
            [``DB.Family``]: List of Family elements in this same category (unwrapped)
        """
        # There has to be a better way, but perhaps not: https://goo.gl/MqdzWg
        symbols = self.symbols
        unique_family_ids = set()
        for symbol in symbols:
            symbol_family = Element(symbol).family
            unique_family_ids.add(symbol_family.Id)
        return [revit.doc.GetElement(family_id) for family_id in unique_family_ids]

    @property
    def symbols(self):
        """Returns:
            [``DB.FamilySymbol``]: List of Symbol Types in the Category (unwrapped)
        """
        return rpw.db.Collector(of_category=self._builtin_enum, is_type=True).elements

    @property
    def instances(self):
        """Returns:
            [``DB.FamilyInstance``]: List of Symbol Instances in the Category (unwrapped)
        """
        return rpw.db.Collector(of_category=self._builtin_enum, is_not_type=True).elements

    @property
    def _builtin_enum(self):
        """ Returns BuiltInCategory of the Category """
        return BicEnum.from_category_id(self._revit_object.Id)

    def __repr__(self):
        return super(Category, self).__repr__({'name': self.name})
