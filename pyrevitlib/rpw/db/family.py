"""
Family Model Wrappers

"""  #

import rpw
from rpw import revit, DB
from rpw.db.element import Element
from rpw.base import BaseObjectWrapper
from rpw.exceptions import RpwException
from rpw.utils.logger import logger
from rpw.db.builtins import BicEnum


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
        # TODO: Add setter - maybe as a mixin
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
