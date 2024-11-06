# -*- coding: UTF-8 -*-
from pyrevit import script, revit, DB, DOCS
from pyrevit.preflight import PreflightTestCase

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
    output.print_md("# Grids Data Lister")
    count = grids_count()
    output.print_md("## Number of grids: {0}".format(count))
    names = grids_names() # [1,2,3,4]
    types = grids_types() # [bubble, bubble, bubble, bubble]
    pinned = grids_pinned() # [True, False, True, False]
    scoper = grids_scoped() # [Name of scope, Name of scope, Name of scope, Name of scope]
    output.print_table(table_data=zip(names, types, pinned, scoper), title="Grids", columns=["Name", "Type", "Pinned", "Scope Box"])



class ModelChecker(PreflightTestCase):
    """
    List grids, if they are pinned, scoped boxed, or named

    This QC tools returns you with the following data:
        Grids count, name, type, pinned status

    """

    name = "Grids Data Lister"
    author = "Jean-Marc Couffin"


    def startTest(self, doc, output):
        checkModel(doc, output)
