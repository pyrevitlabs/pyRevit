from pyrevit.coreutils.logger import get_logger

# noinspection PyUnresolvedReferences
from System.Collections.Generic import List
# noinspection PyUnresolvedReferences
from Autodesk.Revit.DB import ElementId
# noinspection PyUnresolvedReferences
from Autodesk.Revit.UI.Selection import ObjectType


logger = get_logger(__name__)


class SelectionUtils:
    def __init__(self, document, uidocument):
        self._doc = document
        self._uidoc = uidocument
        self._uidoc_selection = self._uidoc.Selection
        self._refs = []

    def _pick_obj(self, obj_type, pick_message, multiple=False, world=False):
        try:
            logger.debug('Picking elements: {} pick_message: {} multiple: {} world: {}'.format(obj_type, pick_message,
                                                                                               multiple, world))
            if multiple:
                self._refs = list(self._uidoc_selection.PickObjects(obj_type, pick_message))
            else:
                self._refs = []
                self._refs.append(self._uidoc_selection.PickObject(obj_type, pick_message))

            if not self._refs:
                logger.debug('Nothing picked by user...Returning None')
                return None

            logger.debug('Picked elements are: {}'.format(self._refs))

            if obj_type == ObjectType.Element:
                return_values = [self._doc.GetElement(ref) for ref in self._refs]
            elif obj_type == ObjectType.PointOnElement:
                if world:
                    return_values = [ref.GlobalPoint for ref in self._refs]
                else:
                    return_values = [ref.UVPoint for ref in self._refs]
            else:
                return_values =  [self._doc.GetElement(ref).GetGeometryObjectFromReference(ref) for ref in self._refs]

            logger.debug('Processed return elements are: {}'.format(return_values))

            if type(return_values) is list:
                if len(return_values) > 1:
                    return return_values
                elif len(return_values) == 1:
                    return return_values[0]
            else:
                logger.error('Error processing picked elements. return_values should be a list.')
        except:
            return None

    def pick_element(self, pick_message=''):
        return self._pick_obj(ObjectType.Element, pick_message)

    def pick_elementpoint(self, pick_message='', world=False):
        return self._pick_obj(ObjectType.PointOnElement, pick_message, world=world)

    def pick_edge(self, pick_message=''):
        return self._pick_obj(ObjectType.Edge, pick_message)

    def pick_face(self, pick_message=''):
        return self._pick_obj(ObjectType.Face, pick_message)

    def pick_linked(self, pick_message=''):
        return self._pick_obj(ObjectType.LinkedElement, pick_message)

    def pick_elements(self, pick_message=''):
        return self._pick_obj(ObjectType.Element, pick_message, multiple=True)

    def pick_elementpoints(self, pick_message='', world=False):
        return self._pick_obj(ObjectType.PointOnElement, pick_message, multiple=True, world=world)

    def pick_edges(self, pick_message=''):
        return self._pick_obj(ObjectType.Edge, pick_message, multiple=True)

    def pick_faces(self, pick_message=''):
        return self._pick_obj(ObjectType.Face, pick_message, multiple=True)

    def pick_linkeds(self, pick_message=''):
        return self._pick_obj(ObjectType.LinkedElement, pick_message, multiple=True)

    def pick_point(self, pick_message=''):
        try:
            return self._uidoc_selection.PickPoint(pick_message)
        except:
            return None

    @property
    def references(self):
        return self._refs


class CurrentElementSelection:
    def __init__(self, document, uidocument):
        self._doc = document
        self._uidoc = uidocument
        self._uidoc_selection = self._uidoc.Selection

        self.elements = [self._doc.GetElement(el_id) for el_id in self._uidoc_selection.GetElementIds()]

        self.utils = SelectionUtils(self._doc, self._uidoc)

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
            if isinstance(el, ElementId):
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
        self._uidoc.Selection.SetElementIds(List[ElementId](self._get_element_ids(element_list)))
        self._uidoc.RefreshActiveView()

    def append(self, element_list):
        new_elids = self._get_element_ids(element_list)
        new_elids.extend(self.element_ids)
        self._uidoc.Selection.SetElementIds(List[ElementId](new_elids))
        self.elements = [self._doc.GetElement(el_id) for el_id in new_elids]
