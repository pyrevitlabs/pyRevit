# noinspection PyUnresolvedReferences
from System.Collections.Generic import List
# noinspection PyUnresolvedReferences
from Autodesk.Revit.DB import ElementId
# noinspection PyUnresolvedReferences
from Autodesk.Revit.UI.Selection import ObjectType


class SelectionUtils:
    def __init__(self, document, uidocument):
        self._doc = document
        self._uidoc = uidocument
        self._uidoc_selection = self._uidoc.Selection
        self._refs = []

    def _pick_obj(self, obj_type, pick_message, multiple=False, world=False):
        try:
            self._refs = []

            if multiple:
                self._refs = list(self._uidoc_selection.PickObjects(obj_type, pick_message))
            else:
                self._refs.append(self._uidoc_selection.PickObject(obj_type, pick_message))

            if obj_type == ObjectType.Element:
                return [doc.GetElement(ref) for ref in self._refs]
            elif obj_type == ObjectType.PointOnElement:
                if world:
                    return [ref.GlobalPoint for ref in self._refs]
                else:
                    return [ref.UVPoint for ref in self._refs]
            else:
                return [doc.GetElement(ref).GetGeometryObjectFromReference(ref) for ref in self._refs]
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

    def replace_selection(self, el_id_list):
        self._uidoc_selection.SetElementIds(List[ElementId](el_id_list))
