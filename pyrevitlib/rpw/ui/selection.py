"""
`uidoc.Selection` Wrapper
"""
import sys

import rpw
from rpw import revit, DB, UI
from rpw.utils.dotnet import List
from rpw.base import BaseObjectWrapper, BaseObject
from rpw.exceptions import RpwTypeError, RevitExceptions
from rpw.utils.logger import logger
from rpw.utils.coerce import to_element_ids, to_elements, to_iterable
from rpw.db.collection import ElementSet
from rpw.db.reference import Reference
from rpw.db.xyz import XYZ
from rpw.db.element import Element

if revit.host and revit.doc:
    ObjectType = UI.Selection.ObjectType
    ObjectSnapTypes = UI.Selection.ObjectSnapTypes
    PickObjects = revit.uidoc.Selection.PickObjects
    PickObject = revit.uidoc.Selection.PickObject
    PickElementsByRectangle = revit.uidoc.Selection.PickElementsByRectangle
    PickBox = revit.uidoc.Selection.PickBox
    PickPoint = revit.uidoc.Selection.PickPoint


class Selection(BaseObjectWrapper, ElementSet):
    """
    >>> from rpw import ui
    >>> selection = ui.Selection()
    >>> selection[0]
    FirstElement
    >>> selection.element_ids
    [ SomeElementId, SomeElementId, ...]
    >>> selection.elements
    [ SomeElement, SomeElement, ...]
    >>> len(selection)
    2

    Wrapped Element:
        _revit_object = `Revit.UI.Selection`
    """

    _revit_object_class = UI.Selection.Selection

    def __init__(self, elements_or_ids=None, uidoc=revit.uidoc):
        """
        Initializes Selection. Elements or ElementIds are optional.
        If no elements are provided on intiialization,
        selection handler will be created with selected elements.

        Args:
            elements ([DB.Element or DB.ElementID]): Elements or ElementIds

        >>> selection = Selection(SomeElement)
        >>> selection = Selection(SomeElementId)
        >>> selection = Selection([Element, Element, Element, ...])

        """

        BaseObjectWrapper.__init__(self, uidoc.Selection)
        self.uidoc = uidoc

        if not elements_or_ids:
            # Is List of elements is not provided, uses uidoc selection
            elements_or_ids = [e for e in uidoc.Selection.GetElementIds()]

        ElementSet.__init__(self, elements_or_ids, doc=self.uidoc.Document)

    def add(self, elements_or_ids, select=True):
        """ Adds elements to selection.

        Args:
            elements ([DB.Element or DB.ElementID]): Elements or ElementIds

        >>> selection = Selection()
        >>> selection.add(SomeElement)
        >>> selection.add([elements])
        >>> selection.add([element_ids])
        """
        # Call Set for proper adding into set.
        ElementSet.add(self, elements_or_ids)
        if select:
            self.update()

    def update(self):
        """ Forces UI selection to match the Selection() object """
        self._revit_object.SetElementIds(self.get_element_ids(as_list=True))

    def clear(self):
        """ Clears Selection

        >>> selection = Selection()
        >>> selection.clear()

        Returns:
            None
        """
        ElementSet.clear(self)
        self.update()

    def __getitem__(self, index):
        """
        Overrides ElementSet __getitem__ to retrieve from selection
        based on index.
        """
        # https://github.com/gtalarico/revitpythonwrapper/issues/32
        for n, element in enumerate(self.__iter__()):
            if n ==index:
                return element
        else:
            raise IndexError('Index is out of range')

    def __bool__(self):
        """
        Returns:
            bool: `False` if selection  is empty, `True` otherwise

        >>> len(selection)
        2
        >>> Selection() is True
        True
        """
        return super(Selection, obj).__bool__()

    def __repr__(self):
        return super(Selection, self).__repr__(data={'count': len(self)})


class Pick(BaseObject):
    """ Pick Class

    Handles all pick* methods in the Seletion Class

    >>> from rpw import ui
    >>> ui.Pick.pick_element()
    <rpw:reference>
    >>> ui.Pick.pick_element(multiple=True)
    [<rpw:reference>, ...]
    """

    @classmethod
    def _pick(cls, obj_type, msg='Pick:', multiple=False, linked=False):
        """ Note: Moved Reference Logic to Referenc Wrapper."""

        try:
            if multiple:
                references = PickObjects(obj_type, msg)
            else:
                reference = PickObject(obj_type, msg)
        except RevitExceptions.OperationCanceledException:
            logger.debug('ui.Pick aborted by user')
            sys.exit(0)

        if multiple:
            return [Reference(ref, linked=linked) for ref in references]
        else:
            return Reference(reference, linked=linked)

    @classmethod
    def pick_box(cls, msg, style='directional'):
        """
        PickBox

        Returns:
            XYZ Points (``XYZ``): Min and Max Points of Box
        """
        # This seems kind of usless right now.
        PICK_STYLE = {'crossing': UI.Selection.PickBoxStyle.Crossing,
                      'enclosing': UI.Selection.PickBoxStyle.Enclosing,
                      'directional': UI.Selection.PickBoxStyle.Directional,
                      }

        pick_box = PickBox(PICK_STYLE[style])
        return (XYZ(pick_box.Min), XYZ(pick_box.Max))

    @classmethod
    def pick_by_rectangle(cls, msg):
        """
        PickBox

        Returns:
            Elements (``List``): List of wrapped Elements
        """
        # TODO: Implement ISelectFilter overload
        # NOTE: This is the only method that returns elements
        refs = PickElementsByRectangle(msg)
        return [Element(ref) for ref in refs]

    @classmethod
    def pick_element(cls, msg='Pick Element(s)', multiple=False):
        """
        Pick Element

        Args:
            msg (str): Message to show
            multiple (bool): False to pick single element, True for multiple

        Returns:
            reference (``Reference``): :any:`Reference` Class
        """
        return cls._pick(ObjectType.Element, msg=msg, multiple=multiple)

    @classmethod
    def pick_pt_on_element(cls, msg='Pick Pt On Element(s)', multiple=False):
        """
        Pick Point On Element

        Args:
            msg (str): Message to show
            multiple (bool): False to pick single point, True for multiple

        Returns:
            reference (``Reference``): :any:`Reference` Class
        """
        return cls._pick(ObjectType.PointOnElement, msg=msg, multiple=multiple)

    @classmethod
    def pick_edge(cls, msg='Pick Edge(s)', multiple=False):
        """
        Pick Edge

        Args:
            msg (str): Message to show
            multiple (bool): False to pick single edge, True for multiple

        Returns:
            reference (``Reference``): :any:`Reference` Class
        """
        return cls._pick(ObjectType.Edge, msg=msg, multiple=multiple)

    @classmethod
    def pick_face(cls, msg='Pick Face(s)', multiple=False):
        """
        Pick Face

        Args:
            msg (str): Message to show
            multiple (bool): False to pick single face, True for multiple

        Returns:
            reference (``Reference``): :any:`Reference` Class
        """
        return cls._pick(ObjectType.Face, msg=msg, multiple=multiple)

    @classmethod
    def pick_linked_element(cls, msg='Pick Linked Element', multiple=False):
        """
        Pick Linked Element

        Args:
            msg (str): Message to show
            multiple (bool): False to pick single element, True for multiple

        Returns:
            reference (``Reference``): :any:`Reference` Class
        """
        return cls._pick(ObjectType.LinkedElement, msg=msg, multiple=multiple, linked=True)

    @classmethod
    def pick_pt(cls, msg='Pick Point', snap=None):
        """
        Pick Point location

        Args:
            msg (str): Message to show
            snap (str): Snap Options: [endpoints, midpoints, nearest,
                                       workplanegrid, intersections,
                                       centers, perpendicular,
                                       tangents, quadrants, points]

        Returns:
            XYZ (`Xyz`): Rpw XYZ Point
        """

        SNAPS = {
                 'none': ObjectSnapTypes["None"],
                 'endpoints': ObjectSnapTypes.Endpoints,
                 'midpoints': ObjectSnapTypes.Midpoints,
                 'nearest': ObjectSnapTypes.Nearest,
                 'workplanegrid': ObjectSnapTypes.WorkPlaneGrid,
                 'intersections': ObjectSnapTypes.Intersections,
                 'centers': ObjectSnapTypes.Centers,
                 'perpendicular': ObjectSnapTypes.Perpendicular,
                 'tangents': ObjectSnapTypes.Tangents,
                 'quadrants': ObjectSnapTypes.Quadrants,
                 'points': ObjectSnapTypes.Points,
                 }

        if snap:
            return XYZ(PickPoint(SNAPS[snap], msg))
        else:
            return XYZ(PickPoint(msg))


class SelectionFilter(UI.Selection.ISelectionFilter):
    # http://www.revitapidocs.com/2017.1/d552f44b-221c-0ecd-d001-41a5099b2f9f.htm
    # Also See Ehsan's implementation on pyrevit
    # TODO: Implement ISelectFilter overload
    def __init__(self):
        raise NotImplemented
