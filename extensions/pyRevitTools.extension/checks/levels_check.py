# -*- coding: UTF-8 -*-
from pyrevit import script, revit, DB, DOCS
from pyrevit.preflight import PreflightTestCase

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


def levels_elevation(document=doc):
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
    output.print_md("# Level Data Lister")
    count = levels_count()
    output.print_md("## Number of levels: {0}".format(count))
    names = levels_names() # [1,2,3,4]
    types = levels_elevation() # [bubble, bubble, bubble, bubble]
    pinned = levels_pinned() # [True, False, True, False]
    scoper = levels_scoped() # [Name of scope, Name of scope, Name of scope, Name of scope]
    elevation = levels_elevation() # [1.0, 2.0, 3.0, 4.0]
    output.print_table(table_data=zip(names, types, pinned, scoper, elevation), title="Levels", columns=["Name", "Type", "Pinned", "Scope Box", "Elevation"])



class ModelChecker(PreflightTestCase):
    """
    List levels, if they are pinned, scoped boxed, or named and its elevation.

    This QC tools returns you with the following data:
        Levels count, name, type, pinned status, scope box, and elevation.

    """

    name = "Levels Data Lister"
    author = "Jean-Marc Couffin"

    def setUp(self, doc, output):
        pass

    def startTest(self, doc, output):
        checkModel(doc, output)


    def tearDown(self, doc, output):
        pass

    def doCleanups(self, doc, output):
        pass
