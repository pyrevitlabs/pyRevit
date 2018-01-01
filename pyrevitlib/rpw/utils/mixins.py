""" Collection of Class Mixins """

import rpw
# from rpw import revit, db, DB # Fixes Circular Import
from rpw.exceptions import RpwCoerceError
from rpw.utils.logger import deprecate_warning


class ByNameCollectMixin():

    """ Adds name, by_name(), and by_name_or_element_ref() methods.
    This is for class inheritance only, used to reduce duplication
    """

    @property
    def name(self):
        """ Returns object's Name attribute """
        return self._revit_object.Name

    @classmethod
    def by_name(cls, name):
        """
        Mixin to provide instantiating by a name for classes that are
        collectible. This is a mixin so specifi usage will vary for each for.
        This method will call the :any:`rpw.db.Element.collect`
        method of the class, and return the first element with a
        matching ``.name`` property.

        >>> LinePatternElement.by_name('Dash')
        <rpw:LinePatternElement name:Dash>

        >>> FillPatternElement.by_name('Solid')
        <rpw:FillPatternElement name:Solid>

        """
        e = cls.collect(where=lambda e: e.name.lower() == name.lower()).get_first()
        if e:
            return e
        raise RpwCoerceError('by_name({})'.format(name), cls)

    @classmethod
    def by_name_or_element_ref(cls, reference):
        """
        Mixin for collectible elements.
        This is to help cast elements from name, elemente, or element_id
        """
        if isinstance(reference, str):
            return cls.by_name(reference)
        elif isinstance(reference, rpw.DB.ElementId):
            return rpw.db.Element.from_id(reference)
        else:
            return cls(reference)



class CategoryMixin():

    """ Adds category and get_category methods.
    """

    @property
    def _category(self):
        """
        Default Category Access Parameter. Overwrite on wrapper as needed.
        See Family Wrapper for an example.
        """
        return self._revit_object.Category

    @property
    def category(self):
        """ Wrapped ``DB.Category`` """
        deprecate_warning('.category', 'get_category()')
        return rpw.db.Category(self._category)

    def get_category(self, wrapped=True):
        """ Wrapped ``DB.Category``"""
        return rpw.db.Category(self._category) if wrapped else self._category
