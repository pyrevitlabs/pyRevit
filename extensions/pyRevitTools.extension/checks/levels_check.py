# -*- coding: UTF-8 -*-
import os

from pyrevit import script, DB, DOCS
from pyrevit.coreutils import applocales
from pyrevit.preflight import PreflightTestCase

_XAML = os.path.join(os.path.dirname(os.path.abspath(__file__)), "locale", "Checks.xaml")


def _t(key):
    return applocales.get_locale_string_from_xaml(_XAML, key)


doc = DOCS.doc


def levels_collector(document):
    levels = DB.FilteredElementCollector(document).OfCategory(DB.BuiltInCategory.OST_Levels).WhereElementIsNotElementType()
    return levels


def levels_count(document=doc):
    levels = levels_collector(document)
    count = levels.GetElementCount()
    return count


def levels_names(document=doc):
    levels = levels_collector(document)
    levels_names = []
    for level in levels:
        levels_names.append(level.Name)
    return levels_names


def levels_types(document=doc):
    levels = levels_collector(document)
    levels_types_names = []
    for level in levels:
        level_type = document.GetElement(level.GetTypeId())
        levels_types_names.append(level_type.get_Parameter(DB.BuiltInParameter.SYMBOL_NAME_PARAM).AsString())
    return levels_types_names


def levels_elevation(document=doc):
    levels = levels_collector(document)
    levels_elevations = []
    for level in levels:
        levels_elevations.append(level.get_Parameter(DB.BuiltInParameter.LEVEL_ELEV).AsValueString())
    return levels_elevations


def levels_pinned(document=doc):
    levels = levels_collector(document)
    pinned_levels = []
    for level in levels:
        pinned_levels.append(level.Pinned)
    return pinned_levels


def levels_scoped(document=doc):
    levels = levels_collector(document)
    scoped_levels = []
    for level in levels:
        scope = level.get_Parameter(DB.BuiltInParameter.DATUM_VOLUME_OF_INTEREST).AsElementId()
        scope = document.GetElement(scope)
        if scope:
            scoped_levels.append(scope.Name)
        else:
            scoped_levels.append("None")
    return scoped_levels


def checkModel(doc, output):
    output = script.get_output()
    output.close_others()
    output.print_md("# {}".format(_t("LevelsDataLister")))
    count = levels_count()
    output.print_md("## {0}: {1}".format(_t("NumberOfLevels"), count))
    names = levels_names()
    types = levels_types()
    pinned = levels_pinned()
    scoper = levels_scoped()
    elevation = levels_elevation()
    output.print_table(
        table_data=zip(names, types, pinned, scoper, elevation),
        title=_t("Levels"),
        columns=[
            _t("Name"),
            _t("Type"),
            _t("Pinned"),
            _t("ScopeBox"),
            _t("Elevation"),
        ]
    )


class ModelChecker(PreflightTestCase):
    name = _t("CheckName_LevelsDataLister")
    author = "Jean-Marc Couffin"

    def startTest(self, doc, output):
        checkModel(doc, output)


ModelChecker.__doc__ = _t("CheckDescription_LevelsDataLister")
