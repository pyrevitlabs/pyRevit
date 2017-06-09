import types
from collections import OrderedDict

# noinspection PyUnresolvedReferences
from rpw import DB, RpwException, get_logger, doc, BaseObjectWrapper
from rpw.db.core.element import Element


logger = get_logger(__name__)


class Collector(BaseObjectWrapper):
    FILTER_MAP = {'of_category': 'OfCategory',
                  'of_class': 'OfClass',
                  'owned_by': 'OwnedByView',
                  'is_curve_based': 'WhereElementIsCurveDriven',
                  'is_type': {True: 'WhereElementIsElementType',
                              False: 'WhereElementIsNotElementType'},
                  'is_view_independent':
                      {True: 'WhereElementIsViewIndependent'},
                  'where_passes': 'WherePasses',
                  'all': {True: 'WhereElementIsNotElementType'},
                  'all_types': {True: 'WhereElementIsElementType'}}

    def __init__(self, **filters):
        if 'view' in filters:
            filter_value = filters['view']
            if isinstance(filter_value, DB.View):
                view_id = filter_value.Id
            else:
                view_id = filter_value
            collector = DB.FilteredElementCollector(doc, view_id)
            filters.pop('view')
        else:
            collector = DB.FilteredElementCollector(doc)
        super(Collector, self).__init__(collector)
        self._callable_filter = None
        self.filter(**filters)

    def filter(self, **filters):
        from rpw.db.core.datamodel import Category

        def apply_filter(filter_name, filter_value):
            api_filter = Collector.FILTER_MAP[filter_name]
            if isinstance(api_filter, dict) \
                    and filter_value in api_filter:
                    collector_rule = getattr(self._wrapped_object,
                                             api_filter[filter_value])
                    self._wrapped_object = collector_rule()
            elif filter_name == 'of_category' \
                    and hasattr(filter_value, 'builtin_enum'):
                collector_rule = getattr(self._wrapped_object,
                                         Collector.FILTER_MAP[filter_name])
                self._wrapped_object = \
                    collector_rule(filter_value.builtin_enum())
            elif filter_name == 'owned_by' \
                    and isinstance(filter_value, DB.View):
                collector_rule = getattr(self._wrapped_object,
                                         Collector.FILTER_MAP[filter_name])
                self._wrapped_object = collector_rule(filter_value.Id)
            elif filter_name == 'where_passes' \
                    and isinstance(filter_value, types.FunctionType):
                self._callable_filter = filter_value
            else:
                collector_rule = getattr(self._wrapped_object,
                                         Collector.FILTER_MAP[filter_name])
                self._wrapped_object = collector_rule(filter_value)

        # verify all provided conditions are valid
        for fltr_name, fltr_value in filters.items():
            if fltr_name not in Collector.FILTER_MAP:
                raise RpwException('Collector filter not valid: {}'
                                   .format(fltr_name))
            else:
                apply_filter(fltr_name, fltr_value)

    @property
    def elements(self):
        if self._callable_filter:
            return filter(self._callable_filter,
                          [Element(el) for el in self._wrapped_object])
        else:
            return [Element(el) for el in self._wrapped_object]

    def __bool__(self):
        return bool(self.elements)

    def __len__(self):
        return len(self.elements)

    def __repr__(self, data=None):
        collector_data = OrderedDict({'count': len(self)})
        if data:
            collector_data.update(data)
        return super(Collector, self).__repr__(data=collector_data)

    def __iter__(self):
        return iter(self.elements)

    @property
    def first(self):
        if len(self) > 0:
            return self.elements[0]

    @property
    def last(self):
        if len(self) > 0:
            return self.elements[-1]
