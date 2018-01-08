"""
Usage

>>> from rpw import db
>>> levels = db.Collector(of_category='Levels', is_type=True)
>>> walls = db.Collector(of_class='Wall', where=lambda x: x.parameters['Length'] > 5)
>>> desks = db.Collector(of_class='FamilyInstance', level='Level 1')

Note:
    As of June 2017, these are the filters that have been implemented:

    | ``ElementCategoryFilter`` = ``of_category``
    | ``ElementClassFilter`` = ``of_class``
    | ``ElementIsCurveDrivenFilter`` = ``is_curve_driven``
    | ``ElementIsElementTypeFilter`` = ``is_type`` + ``is_not_type``
    | ``ElementOwnerViewFilter`` = ``view``
    | ``ElementLevelFilter`` = ``level`` + ``not_level``
    | ``ElementOwnerViewFilter`` = ``owner_view`` + ``is_view_independent``
    | ``FamilySymbolFilter`` = ``family``
    | ``FamilyInstanceFilter`` = ``symbol``
    | ``ElementParameterFilter`` = ``parameter_filter``
    | ``Exclusion`` = ``exclude``
    | ``UnionWith`` = ``or_collector``
    | ``IntersectWith`` = ``and_collector``
    | ``Custom`` = where

"""

from rpw import revit, DB
from rpw.utils.dotnet import List
from rpw.base import BaseObjectWrapper, BaseObject
from rpw.exceptions import RpwException, RpwTypeError, RpwCoerceError
from rpw.db.element import Element
from rpw.db.builtins import BicEnum, BipEnum
from rpw.ui.selection import Selection
from rpw.db.collection import ElementSet
from rpw.utils.coerce import to_element_id, to_element_ids
from rpw.utils.coerce import to_category, to_class
from rpw.utils.logger import logger
from rpw.utils.logger import deprecate_warning

# More Info on Performance and ElementFilters:
# http://thebuildingcoder.typepad.com/blog/2015/12/quick-slow-and-linq-element-filtering.html


class BaseFilter(BaseObject):
    """ Base Filter and Apply Logic """

    method = 'WherePasses'

    @classmethod
    def process_value(cls, value):
        """
        Filters must implement this method to process the input values and
        convert it into the proper filter or value.

        For example, if the user inputs `level=Level`,
        process value will create a ElementLevelFilter() with the id of Level.

        Additionally, this method can be used for more advanced input
        processing, for example, converting a 'LevelName' into a Level
        to allow for more flexible input options
        """
        raise NotImplemented

    @classmethod
    def apply(cls, doc, collector, value):
        """
        Filters can overide this method to define how the filter is applied
        The default behavious is to chain the ``method`` defined by the filter
        class (ie. WherePasses) to the collector, and feed it the input `value`
        """
        method_name = cls.method
        method = getattr(collector, method_name)

        # FamilyInstanceFilter is the only Filter that  requires Doc
        if cls is not FilterClasses.FamilyInstanceFilter:
            value = cls.process_value(value)
        else:
            value = cls.process_value(value, doc)

        return method(value)


class SuperQuickFilter(BaseFilter):
    """ Preferred Quick """
    priority_group = 0


class QuickFilter(BaseFilter):
    """ Typical Quick """
    priority_group = 1


class SlowFilter(BaseFilter):
    """ Typical Slow """
    priority_group = 2


class SuperSlowFilter(BaseFilter):
    """ Leave it for Last. Must unpack results """
    priority_group = 3

class LogicalFilter(BaseFilter):
    """ Leave it after Last as it must be completed """
    priority_group = 4

class FilterClasses():
    """
    Groups FilterClasses to facilitate discovery.

    # TODO: Move Filter doc to Filter Classes

    Implementation Tracker:
    Quick
        X Revit.DB.ElementCategoryFilter = of_category
        X Revit.DB.ElementClassFilter = of_class
        X Revit.DB.ElementIsCurveDrivenFilter = is_curve_driven
        X Revit.DB.ElementIsElementTypeFilter = is_type / is_not_type
        X Revit.DB.ElementOwnerViewFilter = view
        X Revit.DB.FamilySymbolFilter = family
        X Revit.DB.ExclusionFilter = exclude
        X Revit.DB.IntersectWidth = and_collector
        X Revit.DB.UnionWidth = or_collector
        _ Revit.DB.BoundingBoxContainsPointFilter
        _ Revit.DB.BoundingBoxIntersectsFilter
        _ Revit.DB.BoundingBoxIsInsideFilter
        _ Revit.DB.ElementDesignOptionFilter
        _ Revit.DB.ElementMulticategoryFilter
        _ Revit.DB.ElementMulticlassFilter
        _ Revit.DB.ElementStructuralTypeFilter
        _ Revit.DB.ElementWorksetFilter
        _ Revit.DB.ExtensibleStorage ExtensibleStorageFilter
    Slow
        X Revit.DB.ElementLevelFilter
        X Revit.DB.FamilyInstanceFilter = symbol
        X Revit.DB.ElementParameterFilter
        _ Revit.DB.Architecture RoomFilter
        _ Revit.DB.Architecture RoomTagFilter
        _ Revit.DB.AreaFilter
        _ Revit.DB.AreaTagFilter
        _ Revit.DB.CurveElementFilter
        _ Revit.DB.ElementIntersectsFilter
        _ Revit.DB.ElementPhaseStatusFilter
        _ Revit.DB.Mechanical SpaceFilter
        _ Revit.DB.Mechanical SpaceTagFilter
        _ Revit.DB.PrimaryDesignOptionMemberFilter
        _ Revit.DB.Structure FamilyStructuralMaterialTypeFilter
        _ Revit.DB.Structure StructuralInstanceUsageFilter
        _ Revit.DB.Structure StructuralMaterialTypeFilter
        _ Revit.DB.Structure StructuralWallUsageFilter
        _ Autodesk.Revit.UI.Selection SelectableInViewFilter

    Logical
        _ Revit.DB.LogicalAndFilter = and_filter
        _ Revit.DB.LogicalOrFilter = or_filter

    Others
        X Custom where - uses lambda

    """
    @classmethod
    def get_available_filters(cls):
        """ Discover all Defined Filter Classes """
        filters = []
        for filter_class_name in dir(FilterClasses):
            if filter_class_name.endswith('Filter'):
                filters.append(getattr(FilterClasses, filter_class_name))
        return filters

    @classmethod
    def get_sorted(cls):
        """ Returns Defined Filter Classes sorted by priority """
        return sorted(FilterClasses.get_available_filters(),
                      key=lambda f: f.priority_group)

    class ClassFilter(SuperQuickFilter):
        keyword = 'of_class'

        @classmethod
        def process_value(cls, class_reference):
            class_ = to_class(class_reference)
            return DB.ElementClassFilter(class_)

    class CategoryFilter(SuperQuickFilter):
        keyword = 'of_category'

        @classmethod
        def process_value(cls, category_reference):
            category = to_category(category_reference)
            return DB.ElementCategoryFilter(category)

    class IsTypeFilter(QuickFilter):
        keyword = 'is_type'

        @classmethod
        def process_value(cls, bool_value):
            return DB.ElementIsElementTypeFilter(not(bool_value))

    class IsNotTypeFilter(IsTypeFilter):
        keyword = 'is_not_type'

        @classmethod
        def process_value(cls, bool_value):
            return DB.ElementIsElementTypeFilter(bool_value)

    class FamilySymbolFilter(QuickFilter):
        keyword = 'family'

        @classmethod
        def process_value(cls, family_reference):
            family_id = to_element_id(family_reference)
            return DB.FamilySymbolFilter(family_id)

    class ViewOwnerFilter(QuickFilter):
        keyword = 'owner_view'
        reverse = False

        @classmethod
        def process_value(cls, view_reference):
            if view_reference is not None:
                view_id = to_element_id(view_reference)
            else:
                view_id = DB.ElementId.InvalidElementId
            return DB.ElementOwnerViewFilter(view_id, cls.reverse)

    class ViewIndependentFilter(QuickFilter):
        keyword = 'is_view_independent'

        @classmethod
        def process_value(cls, bool_value):
            view_id = DB.ElementId.InvalidElementId
            return DB.ElementOwnerViewFilter(view_id, not(bool_value))

    class CurveDrivenFilter(QuickFilter):
        keyword = 'is_curve_driven'

        @classmethod
        def process_value(cls, bool_value):
            return DB.ElementIsCurveDrivenFilter(not(bool_value))

    class FamilyInstanceFilter(SlowFilter):
        keyword = 'symbol'

        @classmethod
        def process_value(cls, symbol_reference, doc):
            symbol_id = to_element_id(symbol_reference)
            return DB.FamilyInstanceFilter(doc, symbol_id)

    class LevelFilter(SlowFilter):
        keyword = 'level'
        reverse = False

        @classmethod
        def process_value(cls, level_reference):
            """ Process level= input to allow for level name """
            if isinstance(level_reference, str):
                level = Collector(of_class='Level', is_type=False,
                                  where=lambda x:
                                  x.Name == level_reference)
                try:
                    level_id = level[0].Id
                except IndexError:
                    RpwCoerceError(level_reference, DB.Level)
            else:
                level_id = to_element_id(level_reference)
            return DB.ElementLevelFilter(level_id, cls.reverse)

    class NotLevelFilter(LevelFilter):
        keyword = 'not_level'
        reverse = True

    class ParameterFilter(SlowFilter):
        keyword = 'parameter_filter'

        @classmethod
        def process_value(cls, parameter_filter):
            if isinstance(parameter_filter, ParameterFilter):
                return parameter_filter.unwrap()
            else:
                raise Exception('Shouldnt get here')

    class WhereFilter(SuperSlowFilter):
        """
        Requires Unpacking of each Element. As per the API design,
        this filter must be combined.

        By default, function will test against wrapped elements for easier
        parameter access

        >>> Collector(of_class='FamilyInstance', where=lambda x: 'Desk' in x.name)
        >>> Collector(of_class='Wall', where=lambda x: 'Desk' in x.parameters['Length'] > 5.0)
        """
        keyword = 'where'

        @classmethod
        def apply(cls, doc, collector, func):
            excluded_elements = set()
            for element in collector:
                wrapped_element = Element(element)
                if not func(wrapped_element):
                    excluded_elements.add(element.Id)
            excluded_elements = List[DB.ElementId](excluded_elements)
            if excluded_elements:
                return collector.Excluding(excluded_elements)
            else:
                return collector

    class ExclusionFilter(QuickFilter):
        keyword = 'exclude'

        @classmethod
        def process_value(cls, element_references):
            element_set = ElementSet(element_references)
            return DB.ExclusionFilter(element_set.as_element_id_list)

    class InteresectFilter(LogicalFilter):
        keyword = 'and_collector'

        @classmethod
        def process_value(cls, collector):
            if hasattr(collector, 'unwrap'):
                collector = collector.unwrap()
            return collector

        @classmethod
        def apply(cls, doc, collector, value):
            new_collector = cls.process_value(value)
            return collector.IntersectWith(new_collector)

    class UnionFilter(InteresectFilter):
        keyword = 'or_collector'

        @classmethod
        def apply(cls, doc, collector, value):
            new_collector = cls.process_value(value)
            return collector.UnionWith(new_collector)


class Collector(BaseObjectWrapper):
    """
    Revit FilteredElement Collector Wrapper

    Usage:
        >>> collector = Collector(of_class='View')
        >>> elements = collector.get_elements()

        Multiple Filters:

        >>> Collector(of_class='Wall', is_not_type=True)
        >>> Collector(of_class='ViewSheet', is_not_type=True)
        >>> Collector(of_category='OST_Rooms', level=some_level)
        >>> Collector(symbol=SomeSymbol)
        >>> Collector(owner_view=SomeView)
        >>> Collector(owner_view=None)
        >>> Collector(parameter_filter=parameter_filter)

        Use Enumeration member or its name as a string:

        >>> Collector(of_category='OST_Walls')
        >>> Collector(of_category=DB.BuiltInCategory.OST_Walls)
        >>> Collector(of_class=DB.ViewType)
        >>> Collector(of_class='ViewType')

        Search Document, View, or list of elements

        >>> Collector(of_category='OST_Walls') # doc is default
        >>> Collector(view=SomeView, of_category='OST_Walls') # Doc is default
        >>> Collector(doc=SomeLinkedDoc, of_category='OST_Walls')
        >>> Collector(elements=[Element1, Element2,...], of_category='OST_Walls')
        >>> Collector(owner_view=SomeView)
        >>> Collector(owner_view=None)

    Attributes:
        collector.get_elements(): Returns list of all `collected` elements
        collector.get_first(): Returns first found element, or ``None``
        collector.get_elements(): Returns list with all elements wrapped.
                                    Elements will be instantiated using :any:`Element`

    Wrapped Element:
        self._revit_object = ``Revit.DB.FilteredElementCollector``

    """

    _revit_object_class = DB.FilteredElementCollector

    def __init__(self, **filters):
        """
        Args:
            **filters (``keyword args``): Scope and filters

        Returns:
            Collector (:any:`Collector`): Collector Instance

        Scope Options:
            * ``view`` `(DB.View)`: View Scope (Optional)
            * ``element_ids`` `([ElementId])`: List of Element Ids to limit Collector Scope
            * ``elements`` `([Element])`: List of Elements to limit Collector Scope

        Warning:
            Only one scope filter should be used per query. If more then one is used,
            only one will be applied, in this order ``view`` > ``elements`` > ``element_ids``

        Filter Options:
            * is_type (``bool``): Same as ``WhereElementIsElementType``
            * is_not_type (``bool``): Same as ``WhereElementIsNotElementType``
            * of_class (``Type``): Same as ``OfClass``. Type can be ``DB.SomeType`` or string: ``DB.Wall`` or ``'Wall'``
            * of_category (``BuiltInCategory``): Same as ``OfCategory``. Can be ``DB.BuiltInCategory.OST_Wall`` or ``'Wall'``
            * owner_view (``DB.ElementId, View`): ``WhereElementIsViewIndependent(True)``
            * is_view_independent (``bool``): ``WhereElementIsViewIndependent(True)``
            * family (``DB.ElementId``, ``DB.Element``): Element or ElementId of Family
            * symbol (``DB.ElementId``, ``DB.Element``): Element or ElementId of Symbol
            * level (``DB.Level``, ``DB.ElementId``, ``Level Name``): Level, ElementId of Level, or Level Name
            * not_level (``DB.Level``, ``DB.ElementId``, ``Level Name``): Level, ElementId of Level, or Level Name
            * parameter_filter (:any:`ParameterFilter`): Applies ``ElementParameterFilter``
            * exclude (`element_references`): Element(s) or ElementId(s) to exlude from result
            * and_collector (``collector``): Collector to intersect with. Elements must be present in both
            * or_collector (``collector``): Collector to Union with. Elements must be present on of the two.
            * where (`function`): function to test your elements against

        """
        # Define Filtered Element Collector Scope + Doc
        collector_doc = filters.pop('doc') if 'doc' in filters else revit.doc

        if 'view' in filters:
            view = filters.pop('view')
            view_id = view if isinstance(view, DB.ElementId) else view.Id
            collector = DB.FilteredElementCollector(collector_doc, view_id)
        elif 'elements' in filters:
            elements = filters.pop('elements')
            element_ids = to_element_ids(elements)
            collector = DB.FilteredElementCollector(collector_doc, List[DB.ElementId](element_ids))
        elif 'element_ids' in filters:
            element_ids = filters.pop('element_ids')
            collector = DB.FilteredElementCollector(collector_doc, List[DB.ElementId](element_ids))
        else:
            collector = DB.FilteredElementCollector(collector_doc)

        super(Collector, self).__init__(collector)

        for key in filters.keys():
            if key not in [f.keyword for f in FilterClasses.get_sorted()]:
                raise RpwException('Filter not valid: {}'.format(key))

        self._collector = self._collect(collector_doc, collector, filters)

    def _collect(self, doc, collector, filters):
        """
        Main Internal Recursive Collector Function.

        Args:
            doc (`UI.UIDocument`): Document for the collector.
            collector (`FilteredElementCollector`): FilteredElementCollector
            filters (`dict`): Filters - {'doc': revit.doc, 'of_class': 'Wall'}

        Returns:
            collector (`FilteredElementCollector`): FilteredElementCollector
        """
        for filter_class in FilterClasses.get_sorted():
            if filter_class.keyword not in filters:
                continue
            filter_value = filters.pop(filter_class.keyword)
            logger.debug('Applying Filter: {}:{}'.format(filter_class, filter_value))
            new_collector = filter_class.apply(doc, collector, filter_value)
            return self._collect(doc, new_collector, filters)
        return collector

    def __iter__(self):
        """ Uses iterator to reduce unecessary memory usage """
        # TODO: Depracate or Make return Wrapped ?
        for element in self._collector:
            yield element

    def get_elements(self, wrapped=True):
        """
        Returns list with all elements instantiated using :any:`Element`
        """
        if wrapped:
            return [Element(el) for el in self.__iter__()]
        else:
            return [element for element in self.__iter__()]

    @property
    def elements(self):
        """ Returns list with all elements """
        deprecate_warning('Collector.elements',
                          'Collector.get_elements(wrapped=True)')
        return self.get_elements(wrapped=False)

    @property
    def wrapped_elements(self):
        """ Returns list with all elements instantiated using :any:`Element`"""
        deprecate_warning('Collector.wrapped_elements',
                          'Collector.get_elements(wrapped=True)')
        return self.get_elements(wrapped=True)

    def select(self):
        """ Selects Collector Elements on the UI """
        Selection(self.element_ids)

    def get_first(self, wrapped=True):
        """
        Returns first element or `None`

        Returns:
            Element (`DB.Element`, `None`): First element or None
        """
        try:
            element = self[0]
            return Element(element) if wrapped else element
        except IndexError:
            return None


    # @property
    # def get_first(self):
    #     deprecate_warning('Collector.first', 'Collector.get_first()')
    #     return self.get_first(wrapped=False)

    def get_element_ids(self):
        """
        Returns list with all elements instantiated using :any:`Element`
        """
        return [element_id for element_id in self._collector.ToElementIds()]

    @property
    def element_ids(self):
        deprecate_warning('Collector.element_ids',
                          'Collector.get_element_ids()')
        return self.get_element_ids()

    def __getitem__(self, index):
        # TODO: Depracate or Make return Wrapped ?
        for n, element in enumerate(self.__iter__()):
            if n == index:
                return element
        else:
            raise IndexError('Index {} not in collector {}'.format(index,
                                                                   self))

    def __bool__(self):
        """ Evaluates to `True` if Collector.elements is not empty [] """
        return bool(self.get_elements(wrapped=False))

    def __len__(self):
        """ Returns length of collector.get_elements() """
        try:
            return self._collector.GetElementCount()
        except AttributeError:
            return len(self.get_elements(wrapped=False))  # Revit 2015

    def __repr__(self):
        return super(Collector, self).__repr__(data={'count': len(self)})


class ParameterFilter(BaseObjectWrapper):
    """
    Parameter Filter Wrapper.
    Used to build a parameter filter to be used with the Collector.

    Usage:
        >>> param_id = DB.ElementId(DB.BuiltInParameter.TYPE_NAME)
        >>> parameter_filter = ParameterFilter(param_id, equals='Wall 1')
        >>> collector = Collector(parameter_filter=parameter_filter)

    Returns:
        FilterRule: A filter rule object, depending on arguments.
    """
    _revit_object_class = DB.ElementParameterFilter

    RULES = {
            'equals': 'CreateEqualsRule',
            'not_equals': 'CreateEqualsRule',
            'contains': 'CreateContainsRule',
            'not_contains': 'CreateContainsRule',
            'begins': 'CreateBeginsWithRule',
            'not_begins': 'CreateBeginsWithRule',
            'ends': 'CreateEndsWithRule',
            'not_ends': 'CreateEndsWithRule',
            'greater': 'CreateGreaterRule',
            'not_greater': 'CreateGreaterRule',
            'greater_equal': 'CreateGreaterOrEqualRule',
            'not_greater_equal': 'CreateGreaterOrEqualRule',
            'less': 'CreateLessRule',
            'not_less': 'CreateLessRule',
            'less_equal': 'CreateLessOrEqualRule',
            'not_less_equal': 'CreateLessOrEqualRule',
           }

    CASE_SENSITIVE = True                 # Override with case_sensitive=False
    FLOAT_PRECISION = 0.0013020833333333  # 1/64" in ft:(1/64" = 0.015625)/12

    def __init__(self, parameter_reference, **conditions):
        """
        Creates Parameter Filter Rule

        >>> param_rule = ParameterFilter(param_id, equals=2)
        >>> param_rule = ParameterFilter(param_id, not_equals='a', case_sensitive=True)
        >>> param_rule = ParameterFilter(param_id, not_equals=3, reverse=True)

        Args:
            param_id(DB.ElementID): ElementId of parameter
            **conditions: Filter Rule Conditions and options.

            conditions:
                | ``begins``, ``not_begins``
                | ``contains``, ``not_contains``
                | ``ends``, ``not_ends``
                | ``equals``, ``not_equals``
                | ``less``, ``not_less``
                | ``less_equal``, ``not_less_equal``
                | ``greater``, ``not_greater``
                | ``greater_equal``, ``not_greater_equal``

            options:
                | ``case_sensitive``: Enforces case sensitive, String only
                | ``reverse``: Reverses result of Collector

        """
        parameter_id = self.coerce_param_reference(parameter_reference)
        reverse = conditions.get('reverse', False)
        case_sensitive = conditions.get('case_sensitive', ParameterFilter.CASE_SENSITIVE)
        precision = conditions.get('precision', ParameterFilter.FLOAT_PRECISION)

        for condition in conditions.keys():
            if condition not in ParameterFilter.RULES:
                raise RpwException('Rule not valid: {}'.format(condition))

        rules = []
        for condition_name, condition_value in conditions.iteritems():

            # Returns on of the CreateRule factory method names above
            rule_factory_name = ParameterFilter.RULES.get(condition_name)
            filter_value_rule = getattr(DB.ParameterFilterRuleFactory,
                                        rule_factory_name)

            args = [condition_value]

            if isinstance(condition_value, str):
                args.append(case_sensitive)

            if isinstance(condition_value, float):
                args.append(precision)

            filter_rule = filter_value_rule(parameter_id, *args)
            if 'not_' in condition_name:
                filter_rule = DB.FilterInverseRule(filter_rule)

            logger.debug('ParamFilter Conditions: {}'.format(conditions))
            logger.debug('Case sensitive: {}'.format(case_sensitive))
            logger.debug('Reverse: {}'.format(reverse))
            logger.debug('ARGS: {}'.format(args))
            logger.debug(filter_rule)
            logger.debug(str(dir(filter_rule)))

            rules.append(filter_rule)
        if not rules:
            raise RpwException('malformed filter rule: {}'.format(conditions))

        _revit_object = DB.ElementParameterFilter(List[DB.FilterRule](rules),
                                                  reverse)
        super(ParameterFilter, self).__init__(_revit_object)
        self.conditions = conditions

    def coerce_param_reference(self, parameter_reference):
        if isinstance(parameter_reference, str):
            param_id = BipEnum.get_id(parameter_reference)
        elif isinstance(parameter_reference, DB.ElementId):
            param_id = parameter_reference
        else:
            RpwCoerceError(parameter_reference, ElementId)
        return param_id

    @staticmethod
    def from_element_and_parameter(element, param_name, **conditions):
        """
        Alternative constructor to built Parameter Filter from Element +
        Parameter Name instead of parameter Id

        >>> parameter_filter = ParameterFilter.from_element(element,param_name, less_than=10)
        >>> Collector(parameter_filter=parameter_filter)
        """
        parameter = element.LookupParameter(param_name)
        param_id = parameter.Id
        return ParameterFilter(param_id, **conditions)

    def __repr__(self):
        return super(ParameterFilter, self).__repr__(data=self.conditions)
