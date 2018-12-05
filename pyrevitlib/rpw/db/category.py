"""
Category Wrapper

"""  #

import rpw
from rpw import revit, DB
from rpw.db.element import Element
from rpw.base import BaseObjectWrapper
from rpw.utils.logger import logger, deprecate_warning
from rpw.db.builtins import BicEnum


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

    def get_families(self, wrapped=True, doc=None):
        """
        Returns:
            Families (``DB.Family``): List of Family elements in this
            same category

        """
        # There has to be a better way, but perhaps not: https://goo.gl/MqdzWg
        unique_family_ids = set()
        for symbol in self.get_symbols(wrapped=True):
            unique_family_ids.add(symbol.family.Id)
        doc = doc or revit.doc
        elements = [doc.GetElement(family_id) for family_id in unique_family_ids]
        return [Element(e) for e in elements] if wrapped else elements

    @property
    def families(self):
        deprecate_warning('Category.families',
                          'Category.get_families(wrapped=True')
        return self.get_families(wrapped=True)

    def get_symbols(self, wrapped=True):
        """
        Returns:
            Symbols (``DB.FamilySymbol``): List of Symbol Types in the Category
        """
        collector = rpw.db.Collector(of_category=self.builtin, is_type=True)
        return collector.get_elements(wrapped)

    @property
    def symbols(self):
        deprecate_warning('Category.symbols',
                          'Category.get_symbols(wrapped=True')
        return self.get_symbols(wrapped=True)

    def get_instances(self, wrapped=True):
        """
        Returns:
            (``DB.FamilyInstance``): List of Symbol Instances in the Category.
        """
        collector = rpw.db.Collector(of_category=self.builtin, is_not_type=True)
        return collector.get_elements(wrapped)

    @property
    def instances(self):
        deprecate_warning('Category.instances',
                          'Category.get_instances(wrapped=True')
        return self.get_instances(wrapped=True)

    @property
    def builtin(self):
        """ Returns BuiltInCategory of the Category """
        return BicEnum.from_category_id(self._revit_object.Id)

    @property
    def _builtin_enum(self):
        deprecate_warning('Category._builtin_enum()', 'Category.builtin')
        return self.builtin

    def __repr__(self):
        return super(Category, self).__repr__({'name': self.name})
