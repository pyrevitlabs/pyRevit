from pyrevit import HOST_APP
from pyrevit import framework, DB, UI
from pyrevit.coreutils.logger import get_logger


logger = get_logger(__name__)


class CurrentElementSelection:
    def __init__(self):
        self.elements = \
            [HOST_APP.doc.GetElement(el_id)
             for el_id in HOST_APP.uidoc.Selection.GetElementIds()]

    def __len__(self):
        return len(self.elements)

    def __iter__(self):
        return iter(self.elements)

    @staticmethod
    def _get_element_ids(mixed_list):
        element_id_list = []

        if not isinstance(mixed_list, list):
            mixed_list = [mixed_list]

        for el in mixed_list:
            if isinstance(el, DB.ElementId):
                element_id_list.append(el)
            else:
                element_id_list.append(el.Id)

        return element_id_list

    @property
    def is_empty(self):
        return len(self.elements) == 0

    @property
    def element_ids(self):
        return [el.Id for el in self.elements]

    @property
    def first(self):
        if self.elements:
            return self.elements[0]

    @property
    def last(self):
        if self.elements:
            return self.elements[len(self)-1]

    def set_to(self, element_list):
        HOST_APP.uidoc.Selection.SetElementIds(
            framework.List[DB.ElementId](
                self._get_element_ids(element_list)
            )
        )
        HOST_APP.uidoc.RefreshActiveView()

    def append(self, element_list):
        new_elids = self._get_element_ids(element_list)
        new_elids.extend(self.element_ids)
        HOST_APP.uidoc.Selection.SetElementIds(
            framework.List[DB.ElementId](new_elids)
        )
        self.elements = \
            [HOST_APP.doc.GetElement(el_id)
             for el_id in new_elids]


def _pick_obj(self, obj_type, pick_message, multiple=False, world=False):
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

        if type(return_values) is list:
            if len(return_values) > 1:
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


def get_selection():
    return CurrentElementSelection()
