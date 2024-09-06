"""
Family Model Wrappers

Relevant remarks from the API Documentation:

Note:
    Custom families within the Revit API represented by three objects -
    Family, FamilySymbol and FamilyInstance .
    Each object plays a significant part in the structure of families.
    The Family element represents the entire family that consists of a
    collection of types, such as an 'I Beam'.
    You can think of that object as representing the entire family file.
    The Family object contains a number of FamilySymbol elements.
    The FamilySymbol object represents a specific set of family settings
    within that Family and represents what is known in the Revit user
    interface as a Type, such as 'W14x32'.
    The FamilyInstance object represents an actual instance of that type
    placed the Autodesk Revit project. For example the FamilyInstance
    would be a single instance of a W14x32 column within the project.

"""  #

import rpw
from rpw import revit, DB
from rpw.db.element import Element
from rpw.base import BaseObjectWrapper
from rpw.exceptions import RpwException
from rpw.utils.logger import logger, deprecate_warning
from rpw.utils.mixins import CategoryMixin
from rpw.db.builtins import BicEnum
from rpw.db.category import Category


class FamilyInstance(Element, CategoryMixin):
    """
    `DB.FamilyInstance` Wrapper

    >>> instance = rpw.db.Element(SomeFamilyInstance)
    <rpw:FamilyInstance % DB.FamilyInstance | name:72" x 36">
    >>> instance.get_symbol().name
    '72" x 36"'
    >>> instance.get_family()
    <RPW_Family:desk>
    >>> instance.get_siblings()
    [<rpw:FamilyInstance % DB.FamilyInstance | name:72" x 36">, ... ]

    Attribute:
        _revit_object (DB.FamilyInstance): Wrapped ``DB.FamilyInstance``
    """

    _revit_object_class = DB.FamilyInstance
    _collector_params = {'of_class': _revit_object_class, 'is_not_type': True}

    def get_symbol(self, wrapped=True):
        """ ``DB.FamilySymbol`` of the ``DB.FamilyInstance`` """
        symbol = self._revit_object.Symbol
        return FamilySymbol(symbol) if wrapped else symbol

    @property
    def symbol(self):
        """ Wrapped ``DB.FamilySymbol`` of the ``DB.FamilyInstance`` """
        deprecate_warning('FamilyInstance.symbol',
                          'FamilyInstance.get_symbol(wrapped=True)')
        return self.get_symbol(wrapped=True)

    def get_family(self, wrapped=True):
        """ Wrapped ``DB.Family`` of the ``DB.FamilyInstance`` """
        symbol = self.get_symbol()
        return symbol.get_family(wrapped=wrapped)

    @property
    def family(self):
        """ Wrapped ``DB.Family`` of the ``DB.FamilyInstance`` """
        deprecate_warning('FamilyInstance.family',
                          'FamilyInstance.get_family(wrapped=True)')
        return self.get_family(wrapped=True)

    def get_siblings(self, wrapped=True):
        """ Other ``DB.FamilyInstance`` of the same ``DB.FamilySymbol`` """
        symbol = self.get_symbol()
        return symbol.get_instances(wrapped=wrapped)

    @property
    def siblings(self):
        """ Other ``DB.FamilyInstance`` of the same ``DB.FamilySymbol`` """
        deprecate_warning('FamilyInstance.siblings',
                          'FamilyInstance.get_siblings(wrapped=True)')
        return self.get_siblings(wrapped=True)

    @property
    def in_assembly(self):
        """
        Returns:
            (bool): True if element is inside an AssemblyInstance
        """
        return self._revit_object.AssemblyInstanceId != DB.ElementId.InvalidElementId

    @property
    def get_assembly(self, wrapped=True):
        """
        Returns:
            (bool, DB.Element) ``None`` if element not in Assembly, else
                returns Element
        """
        if self.in_assembly:
            assembly_id = self._revit_object.AssemblyInstanceId
            assembly = self.doc.GetElement()
            return  Element(assembly) if wrapped else assembly
        else:
            return None

    def __repr__(self):
        symbol_name = self.get_symbol(wrapped=True).name
        return super(FamilyInstance, self).__repr__(data={'symbol': symbol_name})


class FamilySymbol(Element, CategoryMixin):
    """
    `DB.FamilySymbol` Wrapper

    >>> symbol = rpw.db.Element(SomeSymbol)
    <rpw:FamilySymbol % DB.FamilySymbol | name:72" x 36">
    >>> instance.get_symbol().name
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

    def get_family(self, wrapped=True):
        """
        Returns:
            :any:`Family`: Wrapped ``DB.Family`` of the symbol

        """
        family = self._revit_object.Family
        return Family(family) if wrapped else family

    @property
    def family(self):
        """Returns:
            :any:`Family`: Wrapped ``DB.Family`` of the symbol """
        deprecate_warning('FamilySymbol.family',
                          'FamilySymbol.get_family(wrapped=True)')
        return self.get_family(wrapped=True)

    def get_instances(self, wrapped=True):
        """
        Returns:
            [``DB.FamilyInstance``]: List of model instances of
                the symbol (unwrapped)
        """
        collector = rpw.db.Collector(symbol=self._revit_object.Id, is_not_type=True)
        return collector.get_elements(wrapped)

    @property
    def instances(self):
        """
        Returns:
            [``DB.FamilyInstance``]: List of model instances
                of the symbol (unwrapped)
        """
        deprecate_warning('FamilySymbol.instances',
                          'FamilySymbol.get_instances(wrapped=True)')
        return self.get_instances(wrapped=True)

    def get_siblings(self, wrapped=True):
        """
        Returns:
            [``DB.FamilySymbol``]: List of symbol Types
                of the same Family (unwrapped)
        """
        symbols_ids = self._revit_object.GetSimilarTypes()
        return [self.doc.GetElement(i) for i in symbols_ids]
        # Same as: return self.family.symbols

    @property
    def siblings(self):
        deprecate_warning('FamilySymbol.siblings',
                          'FamilySymbol.get_siblings(wrapped=True)')
        return self.get_siblings(wrapped=True)


    def __repr__(self):
        return super(FamilySymbol, self).__repr__(data={'name': self.name})


class Family(Element, CategoryMixin):
    """
    `DB.Family` Wrapper

    Attribute:
        _revit_object (DB.Family): Wrapped ``DB.Family``
    """

    _revit_object_class = DB.Family
    _collector_params = {'of_class': _revit_object_class}

    def get_instances(self, wrapped=True):
        """Returns:
            [``DB.FamilyInstance``]: List of model instances in this family (unwrapped)
        """
        # There has to be a better way
        instances = []
        for symbol in self.get_symbols(wrapped=True):
            symbol_instances = symbol.get_instances(wrapped=wrapped)
            instances.append(symbol_instances)
        return instances

    @property
    def instances(self):
        deprecate_warning('Family.instances',
                          'Family.get_instances(wrapped=True)')
        return self.get_instances(wrapped=True)

    def get_symbols(self, wrapped=True):
        """Returns:
            [``DB.FamilySymbol``]: List of Symbol Types in the family (unwrapped)
        """
        symbols_ids = self._revit_object.GetFamilySymbolIds()
        elements = [self.doc.GetElement(i) for i in symbols_ids]
        return [Element(e) for e in elements] if wrapped else elements

    @property
    def symbols(self):
        deprecate_warning('Family.symbols',
                          'Family.get_symbols(wrapped=True)')
        return self.get_symbols(wrapped=True)

    def get_siblings(self, wrapped=True):
        """Returns:
            [``DB.Family``]: List of Family elements in the same category (unwrapped)
        """
        return self.category.get_families(wrapped=wrapped)

    @property
    def siblings(self):
        """Returns:
            [``DB.Family``]: List of Family elements in the same category (unwrapped)
        """
        return self.get_siblings(wrapped=True)

    @property
    def _category(self):
        """Returns:
            :any:`Category`: Wrapped ``DB.Category`` of the Family """
        return self._revit_object.FamilyCategory

    def __repr__(self):
        return super(Family, self).__repr__({'name': self.name})
