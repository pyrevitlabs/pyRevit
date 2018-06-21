from pyrevit import HOST_APP
from pyrevit import framework, DB, UI
from pyrevit.coreutils.logger import get_logger

from pyrevit.revit import ensure


__all__ = ('pick_element', 'pick_elementpoint', 'pick_edge', 'pick_face',
           'pick_linked', 'pick_elements', 'pick_elementpoints', 'pick_edges',
           'pick_faces', 'pick_linkeds', 'pick_point', 'pick_rectangle',
           'get_selection_category_set', 'get_selection')


logger = get_logger(__name__)


class ElementSelection:
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
            yield HOST_APP.doc.GetElement(elref)

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
        return [HOST_APP.doc.GetElement(x) for x in self._refs]

    @property
    def element_ids(self):
        return self._refs

    @property
    def first(self):
        if self._refs:
            return HOST_APP.doc.GetElement(self._refs[0])

    @property
    def last(self):
        if self._refs:
            return HOST_APP.doc.GetElement(self._refs[-1])

    def set_to(self, element_list):
        self._refs = ElementSelection.get_element_ids(element_list)
        HOST_APP.uidoc.Selection.SetElementIds(
            framework.List[DB.ElementId](self._refs)
            )
        HOST_APP.uidoc.RefreshActiveView()

    def append(self, element_list):
        self._refs.extend(ElementSelection.get_element_ids(element_list))
        self.set_to(self._refs)

    def include(self, element_type):
        refs = [x for x in self._refs
                if isinstance(HOST_APP.doc.GetElement(x),
                              element_type)]
        return ElementSelection(refs)

    def exclude(self, element_type):
        refs = [x for x in self._refs
                if not isinstance(HOST_APP.doc.GetElement(x),
                                  element_type)]
        return ElementSelection(refs)

    def no_views(self):
        return self.exclude(DB.View)

    def only_views(self):
        return self.include(DB.View)


def _pick_obj(obj_type, pick_message, multiple=False, world=False):
    refs = []

    try:
        logger.debug('Picking elements: '
                     '{} pick_message: '
                     '{} multiple: '
                     '{} world: '
                     '{}'.format(obj_type,
                                 pick_message,
                                 multiple, world))
        if multiple:
            refs = list(
                HOST_APP.uidoc.Selection.PickObjects(obj_type, pick_message)
                )
        else:
            refs = []
            refs.append(
                HOST_APP.uidoc.Selection.PickObject(obj_type, pick_message)
                )

        if not refs:
            logger.debug('Nothing picked by user...Returning None')
            return None

        logger.debug('Picked elements are: {}'.format(refs))

        if obj_type == UI.Selection.ObjectType.Element:
            return_values = \
                [HOST_APP.doc.GetElement(ref)
                 for ref in refs]
        elif obj_type == UI.Selection.ObjectType.PointOnElement:
            if world:
                return_values = [ref.GlobalPoint for ref in refs]
            else:
                return_values = [ref.UVPoint for ref in refs]
        else:
            return_values = \
                [HOST_APP.doc.GetElement(ref)
                    .GetGeometryObjectFromReference(ref)
                 for ref in refs]

        logger.debug('Processed return elements are: {}'.format(return_values))

        if len(return_values) > 1 or multiple:
            return return_values
        elif len(return_values) == 1:
            return return_values[0]
        else:
            logger.error('Error processing picked elements. '
                         'return_values should be a list.')
    except Exception:
        return None


def pick_element(pick_message=''):
    return _pick_obj(UI.Selection.ObjectType.Element,
                     pick_message)


def pick_elementpoint(pick_message='', world=False):
    return _pick_obj(UI.Selection.ObjectType.PointOnElement,
                     pick_message,
                     world=world)


def pick_edge(pick_message=''):
    return _pick_obj(UI.Selection.ObjectType.Edge,
                     pick_message)


def pick_face(pick_message=''):
    return _pick_obj(UI.Selection.ObjectType.Face,
                     pick_message)


def pick_linked(pick_message=''):
    return _pick_obj(UI.Selection.ObjectType.LinkedElement,
                     pick_message)


def pick_elements(pick_message=''):
    return _pick_obj(UI.Selection.ObjectType.Element,
                     pick_message,
                     multiple=True)


def pick_elementpoints(pick_message='', world=False):
    return _pick_obj(UI.Selection.ObjectType.PointOnElement,
                     pick_message,
                     multiple=True, world=world)


def pick_edges(pick_message=''):
    return _pick_obj(UI.Selection.ObjectType.Edge,
                     pick_message,
                     multiple=True)


def pick_faces(pick_message=''):
    return _pick_obj(UI.Selection.ObjectType.Face,
                     pick_message,
                     multiple=True)


def pick_linkeds(pick_message=''):
    return _pick_obj(UI.Selection.ObjectType.LinkedElement,
                     pick_message,
                     multiple=True)


def pick_point(pick_message=''):
    try:
        return HOST_APP.uidoc.Selection.PickPoint(pick_message)
    except Exception:
            return None


def pick_rectangle(pick_message='', pick_filter=None):
    if pick_filter:
        return HOST_APP.uidoc.Selection.PickElementsByRectangle(pick_filter,
                                                                pick_message)
    else:
        return HOST_APP.uidoc.Selection.PickElementsByRectangle(pick_message)


def get_selection_category_set():
    selection = ElementSelection()
    cset = DB.CategorySet()
    for element in selection:
        cset.Insert(element.Category)
    return cset


def get_selection():
    return ElementSelection()
