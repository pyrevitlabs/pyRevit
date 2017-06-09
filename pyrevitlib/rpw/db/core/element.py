from collections import OrderedDict

# noinspection PyUnresolvedReferences
from rpw import DB, doc, get_logger, BaseObjectWrapper, BaseObject
from rpw.utils import get_all_subclasses
from rpw.db.core.builtins import BicEnum
from rpw.db.core.parameter import ParameterSet
from rpw.utils.coerce import to_element_ids


logger = get_logger(__name__)


class Element(BaseObjectWrapper):
    """Wrapper for all API Objects that have id
    """
    _wrapped_class = DB.Element

    def __new__(cls, api_obj, enforce_type=None, enforce_types=None):
        def process_class(input_class):
            return super(Element, cls).__new__(input_class)

        def find_category_class(input_class, builtin_cat):
            for categ_class in get_all_subclasses(input_class):
                if hasattr(categ_class, '_wrapped_category') \
                        and builtin_cat == categ_class._wrapped_category:
                    return categ_class

        if isinstance(api_obj, DB.ElementId):
            element = doc.GetElement(api_obj)
        else:
            element = api_obj

        element_type = type(element)    # type: DB.Element

        if element_type == DB.BuiltInCategory:
            cat_class = find_category_class(cls, element)
            return process_class(cat_class)
        elif element_type == DB.Category:
            cat_class = \
                find_category_class(cls, BicEnum.from_category_id(element.Id))
            return process_class(cat_class)
        else:
            for sub_class in get_all_subclasses(cls):   # type: Element
                if isinstance(sub_class._wrapped_class, list) \
                        and element_type in sub_class._wrapped_class:
                    return process_class(sub_class)
                elif element_type == sub_class._wrapped_class:
                    return process_class(sub_class)

        return process_class(cls)

    def __init__(self, api_obj, enforce_type=None, enforce_types=None):
        if isinstance(api_obj, DB.ElementId):
            element = doc.GetElement(api_obj)
        else:
            element = api_obj

        super(Element, self).__init__(element,
                                      enforce_type=enforce_type,
                                      enforce_types=enforce_types)
        self.parameters = ParameterSet(element)

    def __dir__(self):
        element_dir = dir(type(self)) + self.__dict__.keys()
        for param in self.parameters.all:
            clean_name = unicode(param.name).replace(' ', '_').lower()
            # noinspection PyTypeChecker
            element_dir.append(clean_name)
        return set(element_dir)

    def __getattr__(self, attr):
        for param in self.parameters.all:
            if attr == unicode(param.name).replace(' ', '_').lower():
                return param.value

        return super(Element, self).__getattr__(attr)

    def __setattr__(self, attr, value):
        # fixme: set the auto attributes correctly. this crashes
        # for param in self.parameters.all:
        #     if attr == unicode(param.name).replace(' ', '_').lower():
        #         param.value = value

        super(Element, self).__setattr__(attr, value)

    @property
    def id(self):
        return self._wrapped_object.Id.IntegerValue

    def __repr__(self, data=None):
        element_data = OrderedDict({'id': self.id})
        if data:
            element_data.update(data)
        return super(Element, self).__repr__(data=element_data)


class ElementCollection(BaseObject):
    def __init__(self, mixed_list):
        super(ElementCollection, self).__init__()
        self._element_ids = []
        self.set(mixed_list)

    @property
    def unwrapped_elements(self):
        return [doc.GetElement(x) for x in self._element_ids]

    @property
    def elements(self):
        return [Element(x) for x in self.unwrapped_elements]

    def __len__(self):
        return len(self.elements)

    def __iter__(self):
        return iter(self.elements)

    def __getitem__(self, index):
        return self.elements.__getitem__(index)

    def __contains__(self, mixed_list):
        # todo
        pass

    def __bool__(self):
        return bool(self.elements)

    # noinspection PyMethodOverriding
    def __repr__(self, data=None):
        collection_data = OrderedDict({'count': len(self)})
        if data:
            collection_data.update(data)
        return super(ElementCollection, self).__repr__(data=collection_data)

    @property
    def is_empty(self):
        return len(self.elements) == 0

    @property
    def first(self):
        return self[0]

    @property
    def last(self):
        return self[-1]

    def set(self, mixed_list):
        self._element_ids = to_element_ids(mixed_list)

    def append(self, mixed_list):
        self._element_ids.extend(to_element_ids(mixed_list))

    def clear(self):
        # ironpython: has not implemented clear method
        # self._element_ids.clear()
        self._element_ids = []
