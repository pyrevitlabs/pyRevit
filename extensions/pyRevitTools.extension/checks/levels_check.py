# -*- coding: UTF-8 -*-
import sys
import os
# Add current directory to path for local imports
_current_dir = os.path.dirname(os.path.abspath(__file__))
if _current_dir not in sys.path:
    sys.path.insert(0, _current_dir)

from pyrevit import script, revit, DB, DOCS
from pyrevit.preflight import PreflightTestCase
from check_translations import DocstringMeta

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
    from check_translations import get_check_translation
    output = script.get_output()
    output.close_others()
    output.print_md("# {}".format(get_check_translation("LevelsDataLister")))
    count = levels_count()
    output.print_md("## {0}: {1}".format(get_check_translation("NumberOfLevels"), count))
    names = levels_names() # [1,2,3,4]
    types = levels_elevation() # [bubble, bubble, bubble, bubble]
    pinned = levels_pinned() # [True, False, True, False]
    scoper = levels_scoped() # [Name of scope, Name of scope, Name of scope, Name of scope]
    elevation = levels_elevation() # [1.0, 2.0, 3.0, 4.0]
    output.print_table(
        table_data=zip(names, types, pinned, scoper, elevation),
        title=get_check_translation("Levels"),
        columns=[
            get_check_translation("Name"),
            get_check_translation("Type"),
            get_check_translation("Pinned"),
            get_check_translation("ScopeBox"),
            get_check_translation("Elevation")
        ]
    )



class ModelChecker(PreflightTestCase):
    __metaclass__ = DocstringMeta
    _docstring_key = "CheckDescription_LevelsDataLister"
    
    @property
    def name(self):
        from check_translations import get_check_translation
        return get_check_translation("CheckName_LevelsDataLister")
    
    author = "Jean-Marc Couffin"


    def startTest(self, doc, output):
        checkModel(doc, output)
