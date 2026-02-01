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
    from check_translations import get_check_translation
    output = script.get_output()
    output.close_others()
    output.print_md("# {}".format(get_check_translation("GridsDataLister")))
    count = grids_count()
    output.print_md("## {0}: {1}".format(get_check_translation("NumberOfGrids"), count))
    names = grids_names() # [1,2,3,4]
    types = grids_types() # [bubble, bubble, bubble, bubble]
    pinned = grids_pinned() # [True, False, True, False]
    scoper = grids_scoped() # [Name of scope, Name of scope, Name of scope, Name of scope]
    output.print_table(
        table_data=zip(names, types, pinned, scoper),
        title=get_check_translation("Grids"),
        columns=[
            get_check_translation("Name"),
            get_check_translation("Type"),
            get_check_translation("Pinned"),
            get_check_translation("ScopeBox")
        ]
    )



class ModelChecker(PreflightTestCase):
    __metaclass__ = DocstringMeta
    _docstring_key = "CheckDescription_GridsDataLister"
    
    @property
    def name(self):
        from check_translations import get_check_translation
        return get_check_translation("CheckName_GridsDataLister")
    
    author = "Jean-Marc Couffin"


    def startTest(self, doc, output):
        checkModel(doc, output)
