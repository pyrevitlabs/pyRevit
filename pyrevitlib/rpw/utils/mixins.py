""" Collection of Class Mixins """

from rpw import revit, DB
from rpw.db.element import Element
from rpw.exceptions import RpwCoerceError


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
        Mixin to provide instantiating by a name for classes that are collectible.
        This is a mixin so specifi usage will vary for each for.
        This method will call the :any:`collect` method of the class,
        and return the first element with a matching ``Name`` property.
        See implementation for more details.

        >>> LinePatternElement.by_name('Dash')
        <rpw:LinePatternElement name:Dash>

        >>> FillPatternElement.by_name('Solid')
        <rpw:FillPatternElement name:Solid>

        """
        first = cls.collect(where=lambda e: e.name == name).first
        if first:
            return cls(first)
        else:
            raise RpwCoerceError('by_name({})'.format(name), cls)

    @classmethod
    def by_name_or_element_ref(cls, reference):
        """
        Mixin for collectible elements.
        This is to help cast elements from name, elemente, or element_id
        """
        if isinstance(reference, str):
            return cls.by_name(reference)
        elif isinstance(reference, DB.ElementId):
            return Element.from_id(reference)
        else:
            return cls(reference)
