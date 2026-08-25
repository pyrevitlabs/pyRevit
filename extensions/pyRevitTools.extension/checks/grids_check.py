# -*- coding: UTF-8 -*-
import os

from pyrevit import script, DB, DOCS
from pyrevit.coreutils import applocales
from pyrevit.preflight import PreflightTestCase

_XAML = os.path.join(os.path.dirname(os.path.abspath(__file__)), "locale", "Checks.xaml")


def _t(key):
    return applocales.get_locale_string_from_xaml(_XAML, key)


doc = DOCS.doc


def grids_collector(document):
    grids = DB.FilteredElementCollector(document).OfCategory(DB.BuiltInCategory.OST_Grids).WhereElementIsNotElementType()
    return grids


def grids_count(document=doc):
    grids = grids_collector(document)
    count = grids.GetElementCount()
    return count


def grids_names(document=doc):
    grids = grids_collector(document)
    grids_names = []
    for grid in grids:
        grids_names.append(grid.Name)
    return grids_names


def grids_types(document=doc):
    grids = grids_collector(document)
    grids_types = []
    for grid in grids:
        grid_type = document.GetElement(grid.GetTypeId())
        # grid_type = grid.get_Parameter(DB.BuiltInParameter.ELEM_TYPE_PARAM).AsElement()
        grids_types.append(grid_type.get_Parameter(DB.BuiltInParameter.SYMBOL_NAME_PARAM).AsString())
    return grids_types


def grids_pinned(document=doc):
    grids = grids_collector(document)
    pinned_grids = []
    for grid in grids:
        pinned_grids.append(grid.Pinned)
    return pinned_grids


def grids_scoped(document=doc):
    grids = grids_collector(document)
    scoped_grids = []
    for grid in grids:
        scope = grid.get_Parameter(DB.BuiltInParameter.DATUM_VOLUME_OF_INTEREST).AsElementId()
        scope = document.GetElement(scope)
        if scope:
            scoped_grids.append(scope.Name)
        else:
            scoped_grids.append("None")
    return scoped_grids


def checkModel(doc, output):
    output = script.get_output()
    output.close_others()
    output.print_md("# {}".format(_t("GridsDataLister")))
    count = grids_count()
    output.print_md("## {0}: {1}".format(_t("NumberOfGrids"), count))
    names = grids_names()
    types = grids_types()
    pinned = grids_pinned()
    scoper = grids_scoped()
    if count > 0:
        output.print_table(
            table_data=zip(names, types, pinned, scoper),
            title=_t("Grids"),
            columns=[
                _t("Name"),
                _t("Type"),
                _t("Pinned"),
                _t("ScopeBox"),
            ]
        )


class ModelChecker(PreflightTestCase):
    name = _t("CheckName_GridsDataLister")
    author = "Jean-Marc Couffin"

    def startTest(self, doc, output):
        checkModel(doc, output)


ModelChecker.__doc__ = _t("CheckDescription_GridsDataLister")
