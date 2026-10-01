""" API Related Sets and Collections """


from collections import OrderedDict

import rpw
from rpw import revit, DB
from rpw.db.xyz import XYZ
from rpw.db.element import Element
from rpw.base import BaseObject
from rpw.utils.coerce import to_elements, to_element_ids, to_element_id
from rpw.utils.dotnet import List
from rpw.utils.logger import deprecate_warning


class ElementSet(BaseObject):
    """
    Provides helpful methods for managing a set of unique of ``DB.ElementId``
    Sets are unordered.

    >>> element_set = ElementSet([element, element])
    >>> element_set = ElementSet()
    >>> element_set.add(SomeElement)
    >>> SomeElement in element_set
    True
    >>> element_set.clear()

    NOTE:
        Similar to DB.ElementSet, doesnt wrap since there is no advantage

    Args:
        (`DB.Element`, `DB.ElementID`, optional): Elements or Element Ids.

    """

    def __init__(self, elements_or_ids=None, doc=revit.doc):
        self.doc = doc
        self._element_id_set = []
        if elements_or_ids:
            self.add(elements_or_ids)

    def add(self, elements_or_ids):
        """
        Adds elements or element_ids to set. Handles single or list

        Args:
            element_reference (`DB.Element`, DB.Element_ids): Iterable Optional

        """
        element_ids = to_element_ids(elements_or_ids)
        for id_ in element_ids:
            if id_ not in self._element_id_set:
                self._element_id_set.append(id_)

    def pop(self, element_reference, wrapped=True):
        """
        Removed from set using ElementIds

        Args:
            element_reference (DB.ElementId, DB.Element)

        Returns:
            (DB.Element, db.Element)

        """
        element_id = to_element_id(element_reference)
        element = self.__getitem__(element_id)
        self._element_id_set.remove(element_id)
        return element if wrapped else element.unwrap()

    def clear(self):
        """ Clears Set """
        self._element_id_set = []

    @property
    def _elements(self):
        return [self.doc.GetElement(e) for e in self._element_id_set]

    @property
    def _wrapped_elements(self):
        return Element.from_list(self._element_id_set)

    def get_elements(self, wrapped=True, as_list=False):
        """
        Elements in ElementSet

        Args:
            wrapped(bool): True for wrapped Elements. Default is True.
            as_list(bool): True if you want list as List[DB.Element], False
                for regular python list. Default is False.
                If ``as_list`` is True, ``wrapped`` will be set to False.

        Returns:
            Elements (``List``): Elements stored in ElementSet
        """
        if as_list or not wrapped:
            elements = self._elements
            return List[DB.Element](elements) if as_list else elements
        else:
            return self._wrapped_elements

    @property
    def wrapped_elements(self):
        deprecate_warning('ElementSet.wrapped_elements',
                          'ElementSet.get_elements(wrapped=True)')
        return self.get_elements(wrapped=True)

    @property
    def elements(self):
        deprecate_warning('ElementSet.wrapped_elements',
                          'ElementSet.get_elements(wrapped=False)')
        return self.get_elements(wrapped=False)

    @property
    def as_element_list(self):
        """
        Returns:
            IList<DB.Element>
        """
        return self.get_element_ids(as_list=True)

    def get_element_ids(self, as_list=True):
        """
        ElementId of Elements in ElementSet

        Args:
            as_list(bool): True if you want list as List[DB.ElementId], False
                for regular python list. Default is True

        Returns:
            ElementIds (List, List[DB.ElementId]): List of ElementIds Objects

        """
        if as_list:
            return List[DB.ElementId](self._element_id_set)
        else:
            return list(self._element_id_set)

    @property
    def element_ids(self):
        deprecate_warning('ElementSet.element_ids',
                          'ElementSet.get_element_ids(as_list=False)')
        return self.get_element_ids(as_list=False)

    @property
    def as_element_id_list(self):
        deprecate_warning('ElementSet.as_element_id_list',
                          'ElementSet.get_element_ids(as_list=True)')
        return self.get_element_ids(as_list=True)

    def select(self):
        """ Selects Set in UI """
        return rpw.ui.Selection(self._element_id_set)

    def __len__(self):
        return len(self._element_id_set)

    def __iter__(self):
        """ Iterator: Wrapped """
        for element in self._element_id_set:
            yield Element.from_id(element)

    def __getitem__(self, element_reference):
        """
        Get Element from set from an element ElementId

        Args:
            element_reference (DB.Element, DB.ElementID)

        Returns:
            (wrapped_element): Wrapped Element. Raises Key Error if not found.
        """
        eid_key = to_element_id(element_reference)
        for element in self.__iter__():
            if element.Id == eid_key:
                return element
        raise KeyError(eid_key)

    def __contains__(self, element_or_id):
        """
        Checks if selection contains the element Reference.

        Args:
            Reference: Element, ElementId, or Integer

        Returns:
            bool: ``True`` or ``False``
        """
        # TODO Write Tests
        element_id = to_element_id(element_or_id)
        return bool(element_id in self._element_id_set)

    def __bool__(self):
        return bool(self._element_id_set)

    def __repr__(self, data=None):
        return super(ElementSet, self).__repr__(data={'count': len(self)})


class ElementCollection(BaseObject):
    """
    List Collection for managing a list of ``DB.Element``.

    >>> element_set = ElementCollection([element, element])
    >>> element_set = ElementCollection()
    >>> element_set.add(SomeElement)
    >>> SomeElement in element_set
    True
    >>> element_set.clear()

    Args:
        (`DB.Element`, `DB.ElementID`, optional): Elements or Element Ids.
    """
    def __init__(self, elements_or_ids=None, doc=revit.doc):
        self.doc = doc
        self._elements = []
        if elements_or_ids:
            self.append(elements_or_ids)

    def append(self, elements_or_ids):
        """ Adds elements or element_ids to set. Handles single or list """
        elements = to_elements(elements_or_ids)
        for element in elements:
            self._elements.append(element)

    def clear(self):
        """ Clears Set """
        self._elements = []

    def pop(self, index=0, wrapped=True):
        """
        Removed from set using ElementIds

        Args:
            index (``int``): Index of Element [Default: 0]
        """
        element = self._elements.pop(index)
        return Element(element) if wrapped else element

    @property
    def _element_ids(self):
        return [e.Id for e in self._elements]

    @property
    def _wrapped_elements(self):
        return Element.from_list(self._elements)

    def get_elements(self, wrapped=True, as_list=False):
        """
        List of Elements in Collection

        Args:
            wrapped(bool): True for wrapped Elements. Default is True.
            as_list(bool): True if you want list as List[DB.ElementId], False
                for regular python list. Default is True

        Returns:
            Elements (``List``): List of Elements Objects or List[DB.Element]
        """
        elements = self._elements

        if as_list or not wrapped:
            elements = self._elements
            return List[DB.Element](elements) if as_list else elements
        else:
            return self._wrapped_elements

    @property
    def elements(self):
        deprecate_warning('ElementCollection.elements',
                          'ElementCollection.get_elements()')
        return self.get_elements(wrapped=True)

    @property
    def as_element_list(self):
        return self.get_elements(as_list=True)

    def select(self):
        """ Selects Set in UI """
        return rpw.ui.Selection(self._elements)

    def get_element_ids(self, as_list=True):
        """
        ElementId of Elements in ElementCollection

        Args:
            as_list(bool): True if you want list as List[DB.ElementId], False
                for regular python list. Default is True

        Returns:
            ElementIds (List, List[DB.ElementId]): List of ElementIds Objects

        """
        if as_list:
            return List[DB.ElementId](self._element_ids)
        else:
            return self._element_ids

    @property
    def element_ids(self):
        """
        Returns:
            ElementIds (``List``): List of ElementIds Objects
        """
        deprecate_warning('ElementCollection.element_ids',
                          'ElementCollection.get_element_ids()')
        return self.get_element_ids(as_list=False)

    @property
    def as_element_id_list(self):
        """
        Returns:
            IList<DB.Element>
        """
        deprecate_warning('ElementCollection.as_element_id_list',
                          'ElementCollection.get_element_ids()')
        return self.get_element_ids(as_list=True)

    def get_first(self, wrapped=True):
        """ Get First Item in Collection

        Args:
            wrapped (bool): True for wrapped. Default is True.

        Returns:
            (db.Element, DB.Element): First Element, or None if empty.
        """
        try:
            element = self._elements[0]
        except IndexError:
            return None
        else:
            return Element(element) if wrapped else element

    def __iter__(self):
        """ Iterator: Wrapped """
        for wrapped_element in self._wrapped_elements:
            yield wrapped_element

    def __len__(self):
        return len(self._elements)

    def __getitem__(self, index):
        """ Getter: Wrapped """
        for n, wrapped_element in enumerate(self.__iter__()):
            if n == index:
                return wrapped_element
        raise IndexError(index)

    def __contains__(self, element_or_id):
        """
        Checks if selection contains the element Reference.

        Args:
            Reference: Element, ElementId, or Integer

        Returns:
            bool: ``True`` or ``False``
        """
        element_id = to_element_id(element_or_id)
        return bool(element_id in self.get_element_ids(as_list=False))

    def __bool__(self):
        return bool(self._elements)

    def __repr__(self, data=None):
        return super(ElementCollection, self).__repr__(
                                                    data={'count': len(self)})


class XyzCollection(BaseObject):
    """
    Provides helpful methods for managing a
    collection(list) of :any:`XYZ` instances.

    >>> points = [p1,p2,p3,p4, ...]
    >>> point_collection = XyzCollection(points)

    Attributes:
        point_collection.average
        point_collection.min
        point_collection.max
    """
    # TODO: Implement unwrapped return.
    # TODO: Implement Collection methods (Add, pop, as list, etc)

    def __init__(self, points):
        self.points = points if points is not None else []

    def __iter__(self):
        for point in self.points:
            yield point

    @property
    def average(self):
        """
        >>> points = [XYZ(0,0,0), XYZ(4,4,2)]
        >>> points.average
        (2,2,1)

        Returns:
            XYZ (`DB.XYZ`): Average of point collection.

        """
        x_values = [point.X for point in self.points]
        y_values = [point.Y for point in self.points]
        z_values = [point.Z for point in self.points]
        x_avg = sum(x_values) / len(x_values)
        y_avg = sum(y_values) / len(y_values)
        z_avg = sum(z_values) / len(z_values)

        return XYZ(x_avg, y_avg, z_avg)

    @property
    def max(self):
        """
        >>> points = [(0,0,5), (2,2,2)]
        >>> points.max
        (2,2,5)

        Returns:
            XYZ (`DB.XYZ`): Max of point collection.

        """
        x_values = [point.X for point in self.points]
        y_values = [point.Y for point in self.points]
        z_values = [point.Z for point in self.points]
        x_max = max(x_values)
        y_max = max(y_values)
        z_max = max(z_values)
        return XYZ(x_max, y_max, z_max)

    @property
    def min(self):
        """
        >>> points = [(0,0,5), (2,2,2)]
        >>> points.min = (0,0,2)

        Returns:
            XYZ (`DB.XYZ`): Min of point collection.

        """
        x_values = [point.X for point in self.points]
        y_values = [point.Y for point in self.points]
        z_values = [point.Z for point in self.points]
        x_min = min(x_values)
        y_min = min(y_values)
        z_min = min(z_values)
        return XYZ(x_min, y_min, z_min)

    def sorted_by(self, x_y_z):
        """ Sorts Point Collection by axis.

        >>> pts = XyzCollection(XYZ(0,10,0), XYZ(0,0,0))
        >>> pts.sorted_by('y')
        [XYZ(0,0,0), XYZ(0,10,0)]

        Args:
            axis (`str`): Axist to sort by.
        """
        sorted_points = self.points[:]
        sorted_points.sort(key=lambda p: getattr(p, x_y_z.upper()))
        return sorted_points

    def __len__(self):
        return len(self.points)

    def __repr__(self):
        return super(PointCollection, self).__repr__(data=len(self))
