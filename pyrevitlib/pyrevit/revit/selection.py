"""Elements selection utilities."""
from pyrevit import HOST_APP, DOCS, PyRevitException
from pyrevit import framework, DB, UI
from pyrevit.coreutils.logger import get_logger

from pyrevit.revit import ensure
from pyrevit.revit import query
from Autodesk.Revit import Exceptions as RevitExceptions


__all__ = ('pick_element', 'pick_element_by_category',
           'pick_elements', 'pick_elements_by_category',
           'get_picked_elements', 'get_picked_elements_by_category',
           'pick_edge', 'pick_edges',
           'pick_face', 'pick_faces',
           'pick_linked', 'pick_linkeds',
           'pick_elementpoint', 'pick_elementpoints',
           'pick_point', 'pick_rectangle', 'get_selection_category_set',
           'get_selection')


# pylint: disable=W0703,C0302,C0103
mlogger = get_logger(__name__)


class ElementSelection:
    """Element selection handler.

    Args:
        element_list (list[DB.Element]): list of selected elements
    """
    def __init__(self, element_list=None):
        if element_list is None:
            if HOST_APP.uidoc:
                self._refs = \
                    [x for x in HOST_APP.uidoc.Selection.GetElementIds()]
            else:
                self._refs = []
        else:
            self._refs = ElementSelection.get_element_ids(element_list)

    def __len__(self):
        return len(self._refs)

    def __iter__(self):
        for elref in self._refs:
            yield DOCS.doc.GetElement(elref)

    def __getitem__(self, index):
        return self.elements[index]

    def __contains__(self, item):
        if isinstance(item, DB.Element):
            elref = item.Id
        elif isinstance(item, DB.ElementId):
            elref = item
        else:
            elref = DB.ElementId.InvalidElementId
        return elref in self._refs

    @classmethod
    def get_element_ids(cls, mixed_list):
        return ensure.ensure_element_ids(mixed_list)

    @property
    def is_empty(self):
        return len(self._refs) == 0

    @property
    def elements(self):
        return [DOCS.doc.GetElement(x) for x in self._refs]

    @property
    def element_ids(self):
        return self._refs

    @property
    def first(self):
        if self._refs:
            return DOCS.doc.GetElement(self._refs[0])

    @property
    def last(self):
        if self._refs:
            return DOCS.doc.GetElement(self._refs[-1])

    def set_to(self, element_list):
        self._refs = ElementSelection.get_element_ids(element_list)
        HOST_APP.uidoc.Selection.SetElementIds(
            framework.List[DB.ElementId](self._refs)
            )
        HOST_APP.uidoc.RefreshActiveView()

    def clear(self):
        HOST_APP.uidoc.Selection.SetElementIds(
            framework.List[DB.ElementId]([DB.ElementId.InvalidElementId])
        )
        HOST_APP.uidoc.RefreshActiveView()

    def append(self, element_list):
        self._refs.extend(ElementSelection.get_element_ids(element_list))
        self.set_to(self._refs)

    def include(self, element_type):
        refs = [x for x in self._refs
                if isinstance(DOCS.doc.GetElement(x),
                              element_type)]
        return ElementSelection(refs)

    def exclude(self, element_type):
        refs = [x for x in self._refs
                if not isinstance(DOCS.doc.GetElement(x),
                                  element_type)]
        return ElementSelection(refs)

    def no_views(self):
        return self.exclude(DB.View)

    def only_views(self):
        return self.include(DB.View)

    def expand_groups(self):
        expanded_refs = []
        for element in self.elements:
            if isinstance(element, DB.Group):
                expanded_refs.extend(element.GetMemberIds())
            else:
                expanded_refs.append(element.Id)
        self._refs = expanded_refs


class PickByCategorySelectionFilter(UI.Selection.ISelectionFilter):
    def __init__(self, category_id):
        self.category_id = category_id

    # standard API override function
    def AllowElement(self, element):
        if element.Category and self.category_id == element.Category.Id:
            return True
        else:
            return False

    # standard API override function
    def AllowReference(self, refer, point):  # pylint: disable=W0613
        return False


def _pick_obj(obj_type, message, multiple=False, world=False, selection_filter=None):
    mlogger.debug(
        "Picking elements: %s " "message: %s " "multiple: %s " "world: %s",
        obj_type,
        message,
        multiple,
        world,
    )
    picker_func = (
        HOST_APP.uidoc.Selection.PickObjects
        if multiple
        else HOST_APP.uidoc.Selection.PickObject
    )
    try:
        pick_result = (
            picker_func(obj_type, selection_filter, message)
            if selection_filter
            else picker_func(obj_type, message)
        )
    except RevitExceptions.OperationCanceledException:
        mlogger.debug("Operation canceled by user")
        return None
    refs = list(pick_result) if multiple else [pick_result]
    if not refs:
        mlogger.debug("Nothing picked by user")
        return None

    mlogger.debug("Picked elements are: %s", refs)

    if obj_type == UI.Selection.ObjectType.Element:
        return_values = [DOCS.doc.GetElement(ref) for ref in refs]
    elif obj_type == UI.Selection.ObjectType.PointOnElement:
        if world:
            return_values = [ref.GlobalPoint for ref in refs]
        else:
            return_values = [ref.UVPoint for ref in refs]
    else:
        return_values = [
            DOCS.doc.GetElement(ref).GetGeometryObjectFromReference(ref) for ref in refs
        ]

    mlogger.debug("Processed return elements are: %s", return_values)

    if len(return_values) > 1 or multiple:
        return return_values
    if len(return_values) == 1:
        return return_values[0]
    mlogger.error("Error processing picked elements. return_values should be a list.")


def pick_element(message=''):
    """Asks the user to pick an element.

    Args:
        message (str): An optional message to display.

    Returns:
        (Element): element selected by the user.
    """
    return _pick_obj(UI.Selection.ObjectType.Element,
                     message)


def pick_element_by_category(cat_name_or_builtin, message=''):
    """Returns the element of the specified category picked by the user.

    Args:
        cat_name_or_builtin (str): name or built-in category of the element
            to pick.
        message (str, optional): message to display on selection.
            Defaults to ''.

    Returns:
        (Element): picked element.

    Raises:
        PyRevitException: If no category matches the specified name or builtin.
    """
    category = query.get_category(cat_name_or_builtin)
    if category:
        pick_filter = PickByCategorySelectionFilter(category.Id)
        return _pick_obj(UI.Selection.ObjectType.Element,
                         message,
                         selection_filter=pick_filter)
    else:
        raise PyRevitException("Can not determine category id from: {}"
                               .format(cat_name_or_builtin))


def pick_elementpoint(message='', world=False):
    """Returns the element point selected by the user.

    Args:
        message (str, optional): message to display. Defaults to ''.
        world (bool, optional): whether to use world coordinates. Defaults to False.

    Returns:
        (PointOnElement): The selected point.
    """
    return _pick_obj(UI.Selection.ObjectType.PointOnElement,
                     message,
                     world=world)


def pick_edge(message=''):
    """Returns the edge selected by the user.

    Args:
        message (str, optional): message to display. Defaults to ''.

    Returns:
        (Edge): The selected edge.
    """
    return _pick_obj(UI.Selection.ObjectType.Edge,
                     message)


def pick_face(message=''):
    """Returns the face selected by the user.

    Args:
        message (str, optional): message to display. Defaults to ''.

    Returns:
        (Face): The selected face.
    """
    return _pick_obj(UI.Selection.ObjectType.Face,
                     message)


def pick_linked(message=''):
    """Returns the linked element selected by the user.

    Args:
        message (str, optional): message to display. Defaults to ''.

    Returns:
        (LinkedElement): The selected linked element.
    """
    return _pick_obj(UI.Selection.ObjectType.LinkedElement,
                     message)


def pick_elements(message=''):
    """Asks the user to pick multiple elements.

    Args:
        message (str): An optional message to display.

    Returns:
        (list[Element]): elements selected by the user.
    """
    return _pick_obj(UI.Selection.ObjectType.Element,
                     message,
                     multiple=True)


def pick_elements_by_category(cat_name_or_builtin, message=''):
    """Returns the elements of the specified category picked by the user.

    Args:
        cat_name_or_builtin (str): name or built-in category of the elements
            to pick.
        message (str, optional): message to display on selection.
            Defaults to ''.

    Returns:
        (list[Element]): picked elements.

    Raises:
        PyRevitException: If no category matches the specified name or builtin.
    """
    category = query.get_category(cat_name_or_builtin)
    if category:
        pick_filter = PickByCategorySelectionFilter(category.Id)
        return _pick_obj(UI.Selection.ObjectType.Element,
                         message,
                         multiple=True,
                         selection_filter=pick_filter)
    else:
        raise PyRevitException("Can not determine category id from: {}"
                               .format(cat_name_or_builtin))


def get_picked_elements(message=''):
    """Allows the user to pick multple elements, one at a time.

    It keeps asking the user to pick an element until no elements are selected.

    Args:
        message (str, optional): The message to display. Defaults to ''.

    Yields:
        (DB.Element): selected element
    """
    picked_element = True
    while picked_element:
        picked_element = pick_element(message=message)
        if not picked_element:
            break
        yield picked_element


def get_picked_elements_by_category(cat_name_or_builtin, message=''):
    """Pick elements by category.

    Keeps asking the user to pick an element until no elements are selected.

    Args:
        cat_name_or_builtin (str): category name or built-in category.
        message (str, optional): message to display while picking elements.

    Yields:
        (DB.Element): The picked elements from the specified category.
    """
    picked_element = True
    while picked_element:
        picked_element = pick_element_by_category(cat_name_or_builtin,
                                                  message=message)
        if not picked_element:
            break
        yield picked_element


def pick_elementpoints(message='', world=False):
    """Selects element points.

    Args:
        message (str): The message to display when selecting element points.
        world (bool, optional): Select points in world coordinates. Defaults to False.

    Returns:
        (list[PointOnElement]): selected element points.
    """
    return _pick_obj(UI.Selection.ObjectType.PointOnElement,
                     message,
                     multiple=True, world=world)


def pick_edges(message=''):
    """Selects edges.

    Args:
        message (str): The message to display when selecting edges.

    Returns:
        (list[Edge]): selected edges.
    """
    return _pick_obj(UI.Selection.ObjectType.Edge,
                     message,
                     multiple=True)


def pick_faces(message=''):
    """Selects faces.

    Args:
        message (str): The message to display when selecting the faces.

    Returns:
        (list[Face]): selected faces.
    """
    return _pick_obj(UI.Selection.ObjectType.Face,
                     message,
                     multiple=True)


def pick_linkeds(message=''):
    """Selects linked elements.

    Args:
        message (str): The message to display when selecting linked elements.

    Returns:
        (list[LinkedElement]): selected linked elements.
    """
    return _pick_obj(UI.Selection.ObjectType.LinkedElement,
                     message,
                     multiple=True)


def pick_point(message=''):
    """Pick a point from the user interface.

    Args:
        message (str): A message to display when prompting for the point.

    Returns:
        (tuple or None): A tuple representing the picked point as (x, y, z)
            coordinates, or None if no point was picked or an error occurred.
    """
    try:
        return HOST_APP.uidoc.Selection.PickPoint(message)
    except Exception:
        return None


def pick_rectangle(message='', pick_filter=None):
    """Picks elements from the user interface by specifying a rectangular area.

    Args:
        message (str, optional): A custom message to display when prompting
            the user to pick elements. Default is an empty string.
        pick_filter (object, optional): An object specifying the filter to apply
            when picking elements. Default is None.

    Returns:
        (list[DB.ElementId]): The selected elements.
    """
    if pick_filter:
        return HOST_APP.uidoc.Selection.PickElementsByRectangle(pick_filter,
                                                                message)
    else:
        return HOST_APP.uidoc.Selection.PickElementsByRectangle(message)


def get_selection_category_set():
    """Returns a CategorySet with the categories of the selected elements.

    Returns:
        (CategorySet): categories of the selected elements.
    """
    selection = ElementSelection()
    cset = DB.CategorySet()
    for element in selection:
        cset.Insert(element.Category)
    return cset


def get_selection():
    """Returns the current selected items.

    Returns:
        (ElementSelection): the current selected items
    """
    return ElementSelection()
