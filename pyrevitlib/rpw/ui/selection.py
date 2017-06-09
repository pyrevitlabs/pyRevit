# noinspection PyUnresolvedReferences
from rpw import BaseObject, get_logger, DB, UI, doc, uidoc, ElementCollection

import clr
clr.AddReference('System')
# noinspection PyUnresolvedReferences
from System.Collections.Generic import List


logger = get_logger(__name__)


class SelectingUtilities(BaseObject):
    def __init__(self):
        super(SelectingUtilities, self).__init__()
        self._refs = []

    def _pick_obj(self, obj_type, pick_message, multiple=False, world=False):
        try:
            logger.debug('Picking elements: {} '
                         'pick_message: {} '
                         'multiple: {} '
                         'world: {}'.format(obj_type, pick_message,
                                            multiple, world))
            if multiple:
                self._refs = list(uidoc.Selection.PickObjects(obj_type,
                                                              pick_message))
            else:
                self._refs = []
                self._refs.append(uidoc.Selection.PickObject(obj_type,
                                                             pick_message))

            if not self._refs:
                logger.debug('Nothing picked by user...Returning None')
                return None

            logger.debug('Picked elements are: {}'.format(self._refs))

            if obj_type == UI.Selection.ObjectType.Element:
                return_values = [doc.GetElement(ref) for ref in self._refs]
            elif obj_type == UI.Selection.ObjectType.PointOnElement:
                if world:
                    return_values = [ref.GlobalPoint for ref in self._refs]
                else:
                    return_values = [ref.UVPoint for ref in self._refs]
            else:
                return_values = \
                    [doc.GetElement(ref).GetGeometryObjectFromReference(ref)
                     for ref in self._refs]

            logger.debug('Processed return elements are: {}'
                         .format(return_values))

            if type(return_values) is list:
                if len(return_values) > 1:
                    return return_values
                elif len(return_values) == 1:
                    return return_values[0]
            else:
                logger.error('Error processing picked elements. '
                             'return_values should be a list.')
        except:
            return None

    def pick_element(self, pick_message=''):
        return self._pick_obj(UI.Selection.ObjectType.Element, pick_message)

    def pick_elementpoint(self, pick_message='', world=False):
        return self._pick_obj(UI.Selection.ObjectType.PointOnElement,
                              pick_message, world=world)

    def pick_edge(self, pick_message=''):
        return self._pick_obj(UI.Selection.ObjectType.Edge, pick_message)

    def pick_face(self, pick_message=''):
        return self._pick_obj(UI.Selection.ObjectType.Face, pick_message)

    def pick_linked(self, pick_message=''):
        return self._pick_obj(UI.Selection.ObjectType.LinkedElement,
                              pick_message)

    def pick_elements(self, pick_message=''):
        return self._pick_obj(UI.Selection.ObjectType.Element,
                              pick_message, multiple=True)

    def pick_elementpoints(self, pick_message='', world=False):
        return self._pick_obj(UI.Selection.ObjectType.PointOnElement,
                              pick_message, multiple=True, world=world)

    def pick_edges(self, pick_message=''):
        return self._pick_obj(UI.Selection.ObjectType.Edge,
                              pick_message, multiple=True)

    def pick_faces(self, pick_message=''):
        return self._pick_obj(UI.Selection.ObjectType.Face,
                              pick_message, multiple=True)

    def pick_linkeds(self, pick_message=''):
        return self._pick_obj(UI.Selection.ObjectType.LinkedElement,
                              pick_message, multiple=True)

    @staticmethod
    def pick_point(pick_message=''):
        try:
            return uidoc.Selection.PickPoint(pick_message)
        except:
            return None

    @property
    def references(self):
        return self._refs


class Selection(ElementCollection):
    def __init__(self):
        super(Selection, self).__init__(list(uidoc.Selection.GetElementIds()))

    def _update_rvt_selection(self):
        uidoc.Selection.SetElementIds(List[DB.ElementId](self._element_ids))
        uidoc.RefreshActiveView()

    def set(self, mixed_list):
        super(Selection, self).set(mixed_list)
        self._update_rvt_selection()

    def append(self, mixed_list):
        super(Selection, self).append(mixed_list)
        self._update_rvt_selection()

    def clear(self):
        super(Selection, self).clear()
        uidoc.Selection.SetElementIds(List[DB.ElementId]())


selection = Selection()
pick = SelectingUtilities()
