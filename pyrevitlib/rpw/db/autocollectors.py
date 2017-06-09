import re
import sys

# noinspection PyUnresolvedReferences
from rpw import DB, doc
from rpw.utils import get_all_subclasses
from rpw.db.core.datamodel import Category
from rpw.db.core.collector import Collector


# Cleans appreviations in BuiltInCategory names
abbr_cleaner = re.compile('OST_IOS_|OST_IOS|OST_').sub
# Cleans symbols in BuiltInCategory names
sym_cleaner = re.compile('[\[\]<>]').sub
# Replaces caps with _lower e.g. StackedWalls = stacked_walls
# cap_cleaner = re.compile('(?<=[a-z])([A-Z]+)').sub


class CategoryCollector(object):
    _wrapped_category = DB.BuiltInCategory

    @classmethod
    def instances(cls, **filters):
        return Collector(of_category=cls._wrapped_category,
                         is_type=False,
                         **filters).elements

    @classmethod
    def symbols(cls, **filters):
        return Collector(of_category=cls._wrapped_category,
                         is_type=True,
                         **filters).elements

    @classmethod
    def families(cls, **filters):
        pass

    @classmethod
    def category(cls):
        return Category(DB.Category.GetCategory(doc, cls._wrapped_category))

    @classmethod
    def builtin_enum(cls):
        return cls._wrapped_category


class SubCategoryCollector(object):
    pass


class AutoCategoryCollectorModule:
    def __init__(self):
        # all_builtin_cats = \
        #     list(DB.BuiltInCategory.GetValues(DB.BuiltInCategory))
        # all_builtin_cats.remove(DB.BuiltInCategory.INVALID)

        all_builtin_cats = []
        for builtin_cat in DB.BuiltInCategory.GetValues(DB.BuiltInCategory):
            try:
                cat = DB.Category.GetCategory(doc, builtin_cat)
                if cat and cat.Parent is None:
                    all_builtin_cats.append(builtin_cat)
            except:
                pass

        all_existing_category_subclass_names = \
            [x.__name__ for x in get_all_subclasses(CategoryCollector)]

        for builtin_cat in all_builtin_cats:
            type_name = self._make_cat_collector_type_name(unicode(builtin_cat))
            if type_name \
                    and type_name not in all_existing_category_subclass_names:
                self.__dict__[type_name] = \
                    type(type_name, (CategoryCollector,),
                         {'_wrapped_category': builtin_cat,
                          '__module__': __name__})

        self.__all__ = self.__dict__.keys()

    @staticmethod
    def _make_cat_collector_type_name(name_str):
        return sym_cleaner('', abbr_cleaner('', name_str))


sys.modules[__name__] = AutoCategoryCollectorModule()
