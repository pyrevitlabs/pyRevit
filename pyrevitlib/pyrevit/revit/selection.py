from pyrevit import HOST_APP, PyRevitException
from pyrevit import framework, DB, UI
from pyrevit.coreutils.logger import get_logger

from pyrevit.revit import ensure
from pyrevit.revit import query


__all__ = ('pick_element', 'pick_element_by_category',
           'pick_elements', 'pick_elements_by_category',
           'get_picked_elements', 'get_picked_elements_by_category',
           'pick_edge', 'pick_edges',
           'pick_face', 'pick_faces',
           'pick_linked', 'pick_linkeds',
           'pick_elementpoint', 'pick_elementpoints',
           'pick_point', 'pick_rectangle', 'get_selection_category_set',
           'get_selection')


#pylint: disable=W0703,C0302,C0103
mlogger = get_logger(__name__)


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
    refs = []

    try:
        mlogger.debug('Picking elements: %s '
                      'message: %s '
                      'multiple: %s '
                      'world: %s', obj_type, message, multiple, world)

        # decide which picker method to use
        picker_func = HOST_APP.uidoc.Selection.PickObject
        if multiple:
            picker_func = HOST_APP.uidoc.Selection.PickObjects

        # call the correct signature of the picker function
        # if selection filter is provided
        if selection_filter:
            pick_result = \
                picker_func(
                    obj_type,
                    selection_filter,
                    message
                )
        else:
            pick_result = \
                picker_func(
                    obj_type,
                    message
                )

        # process the results
        if multiple:
            refs = list(pick_result)
        else:
            refs = []
            refs.append(pick_result)

        if not refs:
            mlogger.debug('Nothing picked by user...Returning None')
            return None

        mlogger.debug('Picked elements are: %s', refs)

        if obj_type == UI.Selection.ObjectType.Element:
            return_values = \
                [HOST_APP.doc.GetElement(ref)
                 for ref in refs]
        elif obj_type == UI.Selection.ObjectType.PointOnElement:
            if world:
                return_values = [ref.GlobalPoint for ref in refs]
            else:
                return_values = [ref.UVPoint for ref in refs]
        elif obj_type == UI.Selection.ObjectType.LinkedElement:
            return_values = []
            for ref in refs:
                ref_link_id = ref.ElementId
                doc_linked = HOST_APP.doc.GetElement(ref_link_id)\
                    .GetLinkDocument()
                return_values.append(doc_linked.GetElement(ref.LinkedElementId))
        else:
            return_values = \
                [HOST_APP.doc.GetElement(ref)
                 .GetGeometryObjectFromReference(ref)
                 for ref in refs]

        mlogger.debug('Processed return elements are: %s', return_values)

        if len(return_values) > 1 or multiple:
            return return_values
        elif len(return_values) == 1:
            return return_values[0]
        else:
            mlogger.error('Error processing picked elements. '
                          'return_values should be a list.')
    except Exception:
        return None


def pick_element(message=''):
    return _pick_obj(UI.Selection.ObjectType.Element,
                     message)


def pick_element_by_category(cat_name_or_builtin, message=''):
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
    return _pick_obj(UI.Selection.ObjectType.PointOnElement,
                     message,
                     world=world)


def pick_edge(message=''):
    return _pick_obj(UI.Selection.ObjectType.Edge,
                     message)


def pick_face(message=''):
    return _pick_obj(UI.Selection.ObjectType.Face,
                     message)


def pick_linked(message=''):
    return _pick_obj(UI.Selection.ObjectType.LinkedElement,
                     message)


def pick_elements(message=''):
    return _pick_obj(UI.Selection.ObjectType.Element,
                     message,
                     multiple=True)


def pick_elements_by_category(cat_name_or_builtin, message=''):
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
    picked_element = True
    while picked_element:
        picked_element = pick_element(message=message)
        if not picked_element:
            break
        yield picked_element


def get_picked_elements_by_category(cat_name_or_builtin, message=''):
    picked_element = True
    while picked_element:
        picked_element = pick_element_by_category(cat_name_or_builtin,
                                                  message=message)
        if not picked_element:
            break
        yield picked_element


def pick_elementpoints(message='', world=False):
    return _pick_obj(UI.Selection.ObjectType.PointOnElement,
                     message,
                     multiple=True, world=world)


def pick_edges(message=''):
    return _pick_obj(UI.Selection.ObjectType.Edge,
                     message,
                     multiple=True)


def pick_faces(message=''):
    return _pick_obj(UI.Selection.ObjectType.Face,
                     message,
                     multiple=True)


def pick_linkeds(message=''):
    return _pick_obj(UI.Selection.ObjectType.LinkedElement,
                     message,
                     multiple=True)


def pick_point(message=''):
    try:
        return HOST_APP.uidoc.Selection.PickPoint(message)
    except Exception:
        return None


def pick_rectangle(message='', pick_filter=None):
    if pick_filter:
        return HOST_APP.uidoc.Selection.PickElementsByRectangle(pick_filter,
                                                                message)
    else:
        return HOST_APP.uidoc.Selection.PickElementsByRectangle(message)


def get_selection_category_set():
    selection = ElementSelection()
    cset = DB.CategorySet()
    for element in selection:
        cset.Insert(element.Category)
    return cset


def get_selection():
    return ElementSelection()
