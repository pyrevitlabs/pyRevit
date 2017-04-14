import sys
import re

from revitutils._project import doc, uidoc

from revitutils._db.wrappers import APIObjectWrapper, ElementWrapper

# noinspection PyUnresolvedReferences
from Autodesk.Revit.DB import Category, BuiltInCategory, ElementId
# noinspection PyUnresolvedReferences
from Autodesk.Revit.DB import FilteredElementCollector as Fec


abbr_cleaner = re.compile('OST_IOS_|OST_IOS|OST_').sub
sym_cleaner = re.compile('[\[\]<>]').sub
cap_cleaner = re.compile('(?<=[a-z])([A-Z]+)').sub


class Collector(APIObjectWrapper):
    def __init__(self, rvt_obj):
        APIObjectWrapper.__init__(self, rvt_obj)
        self.name = self._make_collector_name(unicode(self._rvt_obj))

    @staticmethod
    def _make_collector_name(name_str):
        return cap_cleaner(r'_\1', sym_cleaner('', abbr_cleaner('', name_str))).lower()

    @property
    def builtin_category(self):
        return self._rvt_obj

    @property
    def category(self):
        return Category.GetCategory(doc, self._rvt_obj)

    def all(self, view=None, **kwargs):
        if view:
            cltr = Fec(doc, ElementId(view.id))
        else:
            cltr = Fec(doc)

        return ElementWrapper.wrap(cltr.OfCategory(self._rvt_obj).WhereElementIsNotElementType().ToElements())

    def types(self, **kwargs):
        return ElementWrapper.wrap(Fec(doc).OfCategory(self._rvt_obj).WhereElementIsElementType().ToElements())


class CollectorModule:
    def __init__(self):
        all_builtin_cats = list(BuiltInCategory.GetValues(BuiltInCategory))
        all_builtin_cats.remove(BuiltInCategory.INVALID)

        for cat in all_builtin_cats:
            collector = Collector(cat)
            if collector.name:
                self.__dict__[collector.name] = collector

        self.__all__ = self.__dict__.keys()


sys.modules[__name__] = CollectorModule()
