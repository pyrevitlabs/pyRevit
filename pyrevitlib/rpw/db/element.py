"""
Element Model Wrappers provide a consitent interface for acccessing parameters and properties
of commonly used elements.

"""  #

import rpw
from rpw import revit, DB
from rpw.db.parameter import Parameter, ParameterSet
from rpw.base import BaseObjectWrapper
from rpw.exceptions import RpwException, RpwWrongStorageType
from rpw.exceptions import RpwParameterNotFound, RpwTypeError
from rpw.utils.logger import logger, deprecate_warning
from rpw.utils.mixins import CategoryMixin
from rpw.db.builtins import BicEnum, BipEnum
from rpw.utils.coerce import to_element_ids


class Element(BaseObjectWrapper, CategoryMixin):
    """
    Inheriting from element extends wrapped elements with a new :class:`parameters`
    attribute, well as the :func:`unwrap` method inherited from the :any:`BaseObjectWrapper` class.

    It can be created by instantiating ``rpw.db.Element`` , or one of the helper
    static methods shown below.

    Most importantly, all other `Element-related` classes inhert from this class
    so it can provide parameter access.

    >>> from rpw import db
    >>> element = db.Element(SomeElement)
    >>> element = db.Element.from_id(ElementId)
    >>> element = db.Element.from_int(Integer)

    >>> wall = db.Element(RevitWallElement)
    >>> wall.Id
    >>> wall.parameters['Height'].value
    10.0

    The ``Element`` Constructor can be used witout specifying the
    exact class. On instantiation, it will attempt to map the type provided,
    if a match is not found, an Element will be used.
    If the element does not inherit from DB.Element, and exception is raised.

    >>> wall_instance = db.Element(SomeWallInstance)
    >>> type(wall_instance)
    'rpw.db.WallInstance'
    >>> wall_symbol = db.Element(SomeWallSymbol)
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

        # TODO: Handle double wrapping
        if hasattr(element, 'unwrap'):
            raise RpwTypeError('revit element', 'wrapped element: {}'.format(element))

        # Ensure Wrapped Element is instance of Class Wrapper or decendent
        if not isinstance(element, _revit_object_class):
            raise RpwTypeError(_revit_object_class.__name__,
                               element.__class__.__name__)

        # Ensure Wrapped Element is instance of Class Wrapper or decendent
        if not isinstance(element, _revit_object_class):
            raise RpwTypeError(_revit_object_class, element.__class__)

        # If explicit constructor was called, use that and skip discovery
        if type(element) is _revit_object_class:
            return super(Element, cls).__new__(cls, element, **kwargs)

        for wrapper_class in defined_wrapper_classes:
            class_name = wrapper_class.__name__
            if type(element) is getattr(wrapper_class, '_revit_object_class', None):
                # Found Mathing Class, Use Wrapper
                # print('Found Mathing Class, Use Wrapper: {}'.format(class_name))
                return super(Element, cls).__new__(wrapper_class, element, **kwargs)
        else:
            # Could Not find a Matching Class, Use Element if related
            return super(Element, cls).__new__(cls, element, **kwargs)

        # No early return. Should not reach this point
        element_class_name = element.__class__.__name__
        raise RpwException('Factory does not support type: {}'.format(element_class_name))

    def __init__(self, element, doc=None):
        """
        Main Element Instantiation

        >>> from rpw import db
        >>> wall = db.Element(SomeElementId)
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
        # rpw.ui.forms.Console(context=locals())
        super(Element, self).__init__(element)
        self.doc = element.Document if doc is None else revit.doc
        if isinstance(element, DB.Element):
            # WallKind Inherits from Family/Element, but is not Element,
            # so ParameterSet fails. Parameters are only added if Element
            # inherits from element
            # NOTE: This is no longer the case. Verify if it can be removed
            self.parameters = ParameterSet(element)

    @property
    def type(self):
        """
        Get's Element Type using the default GetTypeId() Method.
        For some Elements, this is the same as ``element.Symbol`` or ``wall.WallType``

        Args:
            doc (``DB.Document``, optional): Document of Element [default: revit.doc]

        Returns:
            (``Element``): Wrapped ``rpw.db.Element`` element type

        """
        element_type_id = self._revit_object.GetTypeId()
        element_type = self._revit_object.Document.GetElement(element_type_id)
        return Element(element_type)

    @property
    def name(self):
        """ Name Property """
        return DB.Element.Name.__get__(self.unwrap())

    @name.setter
    def name(self, value):
        """ Name Property Setter """
        return DB.Element.Name.__set__(self.unwrap(), value)

    @classmethod
    def collect(cls, **kwargs):
        """
        Collect all elements of the wrapper using the default collector.
        This method is defined on the main Element wrapper, but the
        collector parameters are defined in each wrapper. For example,
        :any:`WallType` uses the `_collector_params`:
        {'of_class': DB.WallType, 'is_type': True}

        These default collector parameters can be overriden by passing keyword
        args to the collectors call.

        >>> from rpw import db
        >>> wall_types_collector = db.WallType.collect()
        <rpw:Collector % FilteredElementCollector [count:4]>
        >>> wall_types_collector.get_elements()  # All Wall Types
        [<rpw:WallType [name:Wall 1] [id:1557]>, ... ]
        >>> wall_types_collector.get_elements()
        [<rpw:Area % DB.Area | Rentable:30.2>]
        >>> rooms = db.WallInstance.collect(level="Level 1")
        [<rpw:WallInstance % DB.Wall symbol:Basic Wall>]

        """
        _collector_params = getattr(cls, '_collector_params', None)

        if _collector_params:
            kwargs.update(_collector_params)
            return rpw.db.Collector(**kwargs)
        else:
            raise RpwException('Wrapper cannot collect by class: {}'.format(cls.__name__))

    @staticmethod
    def from_int(id_int, doc=None):
        """
        Instantiate Element from an Integer representing and Id

        Args:
            id (``int``): ElementId of Element to wrap
            doc (``DB.Document``, optional): Document of Element [default: revit.doc]

        Returns:
            (``Element``): Wrapped ``rpw.db.Element`` instance
        """
        doc = revit.doc if doc is None else doc
        element_id = DB.ElementId(id_int)
        return Element.from_id(element_id, doc=doc)

    @staticmethod
    def from_id(element_id, doc=None):
        """
        Instantiate Element from an ElementId

        Args:
            id (``ElementId``): ElementId of Element to wrap
            doc (``DB.Document``, optional): Document of Element [default: revit.doc]

        Returns:
            (``Element``): Wrapped ``rpw.db.Element`` instance

        """
        doc = doc or revit.doc
        element = doc.GetElement(element_id)
        return Element(element)

    @staticmethod
    def from_list(element_references, doc=None):
        """
        Instantiate Elements from a list of DB.Element instances

        Args:
            elements (``[DB.Element, DB.ElementId]``): List of element references

        Returns:
            (``list``): List of ``rpw.db.Element`` instances

        """
        doc = doc or revit.doc
        try:
            return [Element(e) for e in element_references]
        except RpwTypeError:
            pass
        try:
            element_ids = to_element_ids(element_references)
            return [Element.from_id(id_, doc=doc) for id_ in element_ids]
        except RpwTypeError:
            raise


    @staticmethod
    def Factory(element):
        deprecate_warning('Element.Factory()', replaced_by='Element()')
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
