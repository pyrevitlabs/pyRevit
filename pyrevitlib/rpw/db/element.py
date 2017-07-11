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
        defined_wrapper_classes = rpw.db.__all__

        _revit_object_class = cls._revit_object_class

        if element is None:
            raise RpwTypeError('Element or Element Child', 'None')

        # Ensure Wrapped Element is instance of Class Wrapper or decendent
        # Must also check is element because isinstance(Element, Element) is False
        if not isinstance(element, _revit_object_class):
            # or cls is not Element:
            raise RpwTypeError(_revit_object_class, type(element))

        # rpw.ui.forms.Console()
        for wrapper_class in defined_wrapper_classes:
            class_name = wrapper_class.__name__
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

        Collector will use default params (ie: Room ``{'of_category': 'OST_rooms'}``).
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
