# noinspection PyUnresolvedReferences
from rpw import DB, doc, get_logger
from rpw.db.core.element import Element
from rpw.db.core.collector import Collector


logger = get_logger(__name__)


class Instance(Element):
    _wrapped_class = DB.FamilyInstance
    _collector_params = {'of_class': _wrapped_class,
                         'is_not_type': True}

    def __init__(self, instance, enforce_type=_wrapped_class):
        super(Instance, self).__init__(instance, enforce_type=enforce_type)

    @property
    def uniq_id(self):
        return self._wrapped_object.UniqueId

    @property
    def symbol(self):
        return Symbol(self._wrapped_object.Symbol)

    @property
    def family(self):
        return self.symbol.family

    @property
    def category(self):
        return self.family.category

    @property
    def siblings(self):
        return self.symbol.instances

    def __repr__(self, data=None):
        instance_data = {'symbol_name': self.symbol.name}
        if data:
            instance_data.update(data)
        return super(Instance, self).__repr__(data=instance_data)


class Symbol(Element):
    _wrapped_class = DB.FamilySymbol
    _collector_params = {'of_class': _wrapped_class,
                         'is_type': True}

    def __init__(self, symbol, enforce_type=_wrapped_class):
        super(Symbol, self).__init__(symbol, enforce_type=enforce_type)

    @property
    def uniq_id(self):
        return self._wrapped_object.UniqueId

    @property
    def name(self):
        return self.parameters.builtins['SYMBOL_NAME_PARAM'].value

    @property
    def family(self):
        return Family(self._wrapped_object.Family)

    @property
    def instances(self):
        # todo:
        # return rpw.Collector(symbol=self._wrapped_object.Id,
        #                      is_not_type=True).elements
        return []

    @property
    def siblings(self):
        symbols_ids = self._wrapped_object.GetSimilarTypes()
        return [Symbol(doc.GetElement(x)) for x in symbols_ids]

    @property
    def category(self):
        return self.family.category

    def __repr__(self, data=None):
        symbol_data = {'family_name': self.family.name}
        if data:
            symbol_data.update(data)
        return super(Symbol, self).__repr__(data=symbol_data)


class Family(Element):
    _wrapped_class = DB.Family
    _collector_params = {'of_class': _wrapped_class,
                         'is_type': True}

    def __init__(self, family, enforce_type=DB.Family):
        super(Family, self).__init__(family, enforce_type=enforce_type)

    @property
    def uniq_id(self):
        return self._wrapped_object.UniqueId

    @property
    def name(self):
        return self._wrapped_object.Name

    @property
    def instances(self):
        instances = []
        for symbol in self.symbols:
            instances.extend(symbol.instances)
        return instances

    @property
    def symbols(self):
        symbols_ids = self._wrapped_object.GetFamilySymbolIds()
        return [Symbol(doc.GetElement(x)) for x in symbols_ids]

    @property
    def category(self):
        return Category(self._wrapped_object.FamilyCategory)

    @property
    def siblings(self):
        return self.category.families

    def __repr__(self, data=None):
        family_data = {'category': self.category.name}
        if data:
            family_data.update(data)
        return super(Family, self).__repr__(data=family_data)


class Category(Element):
    _wrapped_class = DB.Category
    _wrapped_category = DB.BuiltInCategory

    def __init__(self, category, enforce_type=DB.Category):
        if type(category) == DB.BuiltInCategory:
            category_obj = DB.Category.GetCategory(doc, category)
        else:
            category_obj = category
        super(Category, self).__init__(category_obj, enforce_type=enforce_type)

    @property
    def builtin_enum(self):
        return self._wrapped_category

    @property
    def name(self):
        return self._wrapped_object.Name

    @property
    def type(self):
        return self._wrapped_object.CategoryType

    @property
    def families(self):
        # todo: take a look at this
        unique_family_ids = set()
        for symbol in self.symbols:
            symbol_family = symbol.family
            unique_family_ids.add(symbol_family.Id)
        return [doc.GetElement(family_id) for family_id in unique_family_ids]

    @property
    def subcategories(self):
        return self._wrapped_object.SubCategories

    @property
    def instances(self):
        return Collector(of_category=self._wrapped_category,
                         is_type=False).elements

    def __repr__(self, data=None):
        return super(Category, self).__repr__(data=data)
